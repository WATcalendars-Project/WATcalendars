#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import re
import asyncio
import time
from datetime import datetime
from urllib.parse import urlparse
import unicodedata

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from groups_loader import load_groups 
from logutils import OK, WARNING as W, ERROR as E, INFO, log, log_entry  
from url_loader import load_url_from_config  
from employees_loader import load_employees  
from playwright.async_api import async_playwright  
from bs4 import BeautifulSoup  

DAY_ALIASES = {
    'pon.': 'MON', 'wt.': 'TUE', 'śr.': 'WED', 'sr.': 'WED', 'czw.': 'THU', 'pt.': 'FRI', 'sob.': 'SAT', 'niedz.': 'SUN'
}

BLOCK_TIME_MAP = {
    '1-2': ("08:00", "09:35"),
    '3-4': ("09:50", "11:25"),
    '5-6': ("11:40", "13:15"),
    '7-8': ("13:30", "15:05"),
    '9-10': ("16:00", "17:35"),
    '11-12': ("17:50", "19:25"),
    '13-14': ("19:40", "21:15"),
}

ROMAN_MONTH = {
    'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5, 'VI': 6,
    'VII': 7, 'VIII': 8, 'IX': 9, 'X': 10, 'XI': 11, 'XII': 12
}

# Regex for date tokens in the format "DD IV" or "DD V"
DATE_TOKEN_RE = re.compile(r'^(\d{2})\s+([IVX]{1,4})$')

TYPE_FULL_MAP = {
    'w': 'Lecture',
    'W': 'Lecture',
    'ć': 'Exercises',
    'c': 'Exercises',  
    'L': 'Laboratory',
    'lab': 'Laboratory',
    'S': 'Seminar',
    'E': 'Exam',
    'Ep': 'Retake exam',
}

TYPE_SYMBOLS = set(TYPE_FULL_MAP.keys())

# Lecturer name display mode: 'auto' | 'always_full' | 'always_short'
LECTURER_NAME_MODE = 'always_full'

ICS_HEADER = [
    "BEGIN:VCALENDAR",
    "VERSION:2.0",
    "PRODID:-//scheduleWTC//EN",
    "CALSCALE:GREGORIAN",
]

OUTPUT_DIR_NAME = "WTC_schedules"


# function to sanitize filenames
def sanitize_filename(filename: str) -> str:
    return re.sub(r'[<>:"\\|?*]', '_', filename)

# Normalize diacritics for comparisons
_strip_diacritic = lambda s: ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')


# Builds a dictionary mapping employee codes to full names with titles.
# Returns tuple: (variant_index, records)
#   variant_index: variant -> {'full': full_with_titles, 'short': short_name}
#   records: list of {'full','short','surname'} for prefix fallback.
TITLE_PATTERN = re.compile(r"^(?:prof\.?\s*(?:dr\s*hab\.)?|dr\s*hab\.|dr\.|mgr\.?|inż\.?|mgr\s*inż\.|lic\.|hab\.|płk\.|ppłk\.|mjr\.|kpt\.|por\.|ppor\.|doc\.|st\.|mł\.)\s+", re.IGNORECASE)
EXTRA_TITLE_SEQ = re.compile(r"^(?:prof\.?\s*WAT)\s+", re.IGNORECASE)
UPPER_ACRO_PREFIX = re.compile(r"^[A-ZĄĆĘŁŃÓŚŹŻ]{2,5}\s+")

def _strip_titles(full_line: str) -> str:
    s = full_line.strip()
    prev = None
    while s and prev != s:
        prev = s
        # First remove combined sequences like 'prof. WAT'
        s = EXTRA_TITLE_SEQ.sub('', s).strip()
        s = TITLE_PATTERN.sub('', s).strip()
    # Remove leftover acronyms (WAT, WITU etc.) if they appear before the name
    changed = True
    while changed:
        changed = False
        m = re.match(r'^(?:[A-ZĄĆĘŁŃÓŚŹŻ]{2,6})\s+(?=[A-ZŻŹĆŁŚÓ][a-ząćęłńóśźż])', s)
        if m:
            s = s[m.end():].strip(); changed = True
    return s

def build_employee_code_index(employees_map: dict):
    variant_index = {}
    records = []
    # Iterate over values to keep titles (keys previously lost titles)
    for full in employees_map.values():
        clean_full = ' '.join(full.split())
        short = _strip_titles(clean_full)
        parts = short.split()
        if len(parts) < 2:
            continue
        first_name = parts[0]
        surname = parts[-1]
        base_surname = _strip_diacritic(re.sub(r'[^A-Za-zĄąĆćĘęŁłŃńÓóŚśŹźŻż]', '', surname))
        base_first = _strip_diacritic(first_name)
        if not base_surname:
            continue
        variants = set()
        # Basic variants
        variants.add(base_surname.lower())
        variants.add(base_surname[:4].lower())
        variants.add(base_surname[:5].lower())
        if base_first:
            variants.add((base_surname[:3] + base_first[0]).lower())
            variants.add((base_first[0] + base_surname).lower())
            variants.add((base_first[0] + base_surname[:4]).lower())
            variants.add((base_surname[:2] + base_first[0]).lower())  # e.g. ch + j => chj (ChJ)
            variants.add((base_surname[:2] + base_first[:2]).lower())  # reserve patterns
            variants.add((base_surname[:3] + base_first[:2]).lower())
        # Explicit initial + full surname
        variants.add((base_first[0] + base_surname).lower())
        rec = {'full': clean_full, 'short': short, 'surname': base_surname.lower()}
        records.append(rec)
        for v in variants:
            if not v:
                continue
            # Do not overwrite an existing mapping (prefer first occurrence)
            variant_index.setdefault(v, {'full': clean_full, 'short': short})
    return variant_index, records

# Extraction of lecturer legend from the right column (code -> full line with titles)
LECTURER_LINE_RE = re.compile(r'^([A-ZŻŹĆŁŚÓ][A-Za-zŻŹĆŁŚÓąćęłńóśźż]{2,12})\s+(.+)$')
TITLE_KEYWORDS = re.compile(r'(prof\.|dr|hab\.|mgr|inż\.|inż|lic\.|płk|ppłk|mjr|kpt|por|ppor)', re.IGNORECASE)
NAME_TOKEN = re.compile(r'^[A-ZŻŹĆŁŚÓ][a-ząćęłńóśźżA-Z]{2,}$')

def _normalize_titles_spacing(text: str) -> str:
    # Ensure dots are followed by a space
    text = re.sub(r'\.(?=\S)', '. ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def extract_lecturer_legend(soup: BeautifulSoup):
    legend = {}
    # 1. Parse textual lines (heuristic)
    for raw in soup.get_text('\n').split('\n'):
        line = raw.strip()
        if len(line) < 3 or len(line) > 160:
            continue
        m = LECTURER_LINE_RE.match(line)
        if not m:
            continue
        code, rest = m.group(1), _normalize_titles_spacing(m.group(2).strip())
        tokens = rest.split()
        cap_tokens = [t for t in tokens if NAME_TOKEN.match(t)]
        if len(cap_tokens) < 2:
            continue
        if not TITLE_KEYWORDS.search(rest) and len(cap_tokens) < 3:
            continue
        legend.setdefault(code, rest)
    # 2. Parse <td mergewith="..."> patterns (legend often stored like this)
    for td in soup.find_all('td'):
        if not td.has_attr('mergewith'):
            continue
        code = td.get_text(strip=True)
        if not code or len(code) > 6:
            continue
        raw_full = td['mergewith']
        full_plain = re.sub('<[^>]+>', ' ', raw_full)
        full_plain = _normalize_titles_spacing(full_plain)
        if not TITLE_KEYWORDS.search(full_plain):
            continue
        tokens = full_plain.split()
        cap_tokens = [t for t in tokens if NAME_TOKEN.match(t)]
        if len(cap_tokens) < 2:
            continue
        legend.setdefault(code, full_plain)
    return legend


# Extend resolve_lecturer_names with extra heuristics for mixed codes (e.g. ChJ, PoS, Nwł, Jg, Ng, PuJ)

def resolve_lecturer_names(codes: list, variant_index, records, mode: str, legend_map=None):
    resolved = []
    legend_map = legend_map or {}
    for raw in codes:
        original_raw = raw
        # Direct match from legend (exact code)
        legend_full = legend_map.get(raw)
        if legend_full:
            resolved.append({'full': legend_full, 'short': _strip_titles(legend_full)})
            continue
        key = _strip_diacritic(raw).lower()
        found = variant_index.get(key)
        if not found:
            for k2 in (key[:5], key[:4], key[:3]):
                if k2 in variant_index:
                    found = variant_index[k2]; break
        # Heuristic: pattern like ChJ / PoS => 2-3 first letters of surname + first name initial
        if not found and re.match(r'^[A-Za-zżźćńółęąśŻŹĆŁŚÓĘĄ]{2,3}[A-Z]$', raw):
            surname_part = key[:-1]
            first_initial = key[-1]
            for rec in records:
                if rec['surname'].startswith(surname_part) and _strip_diacritic(rec['short'].split()[0])[0].lower() == first_initial.lower():
                    found = {'full': rec['full'], 'short': rec['short']}
                    break
        # Heuristic: two-letter codes (Jg, Ng) => start of surname
        if not found and len(key) == 2:
            candidates = [rec for rec in records if rec['surname'].startswith(key)]
            if len(candidates) == 1:
                c = candidates[0]; found = {'full': c['full'], 'short': c['short']}
        if not found and len(key) == 2:
            # Try match first name initial + surname initial (reversed pattern)
            for rec in records:
                short_parts = rec['short'].split()
                if len(short_parts) >= 2:
                    fi = _strip_diacritic(short_parts[0])[0].lower()
                    sn = rec['surname'][0].lower()
                    if key == fi + sn:
                        found = {'full': rec['full'], 'short': rec['short']}; break
        if not found and len(key) == 3:
            # Variant: first letter of surname + first two of first name
            for rec in records:
                short_parts = rec['short'].split()
                if len(short_parts) >= 2:
                    fi2 = _strip_diacritic(short_parts[0])[:2].lower()
                    sn1 = rec['surname'][0].lower()
                    if key == sn1 + fi2:
                        found = {'full': rec['full'], 'short': rec['short']}; break
        if not found and len(key) == 3:
            # Variant: first name initial + first two letters of surname
            for rec in records:
                fi = _strip_diacritic(rec['short'].split()[0])[0].lower()
                sn2 = rec['surname'][:2].lower()
                if key == fi + sn2:
                    found = {'full': rec['full'], 'short': rec['short']}; break
        if not found:
            for rec in records:
                if rec['surname'].startswith(key[:3]):
                    found = {'full': rec['full'], 'short': rec['short']}; break
        if not found:
            # If legend has a full line containing code as token (rare) attempt search
            for code2, full_line in legend_map.items():
                if raw.lower() in full_line.lower().split():
                    legend_full2 = full_line
                    found = {'full': legend_full2, 'short': _strip_titles(legend_full2)}
                    break
        if not found:
            found = {'full': raw, 'short': raw, 'unresolved': original_raw}
        resolved.append(found)
    # Output mode selection
    if mode == 'always_full':
        return [r['full'] for r in resolved]
    if mode == 'always_short':
        return [r['short'] for r in resolved]
    any_no_title = any(r['full'] == r['short'] for r in resolved)
    if any_no_title:
        return [r['short'] for r in resolved]
    return [r['full'] for r in resolved]


# Heuristic for extracting legend (abbreviation -> full name)
LEGEND_LINE_RE = re.compile(r'^(?P<abbr>[A-Za-zĄąĆćĘęŁłŃńÓóŚśŹźŻż0-9]{1,15})\s*[–\-:\u2013]\s+(?P<full>.+)$')


def extract_legend_maps(soup: BeautifulSoup, schedule_table=None):
    subject_map = {}
    full_text = soup.get_text('\n')
    # Cells with mergewith attribute
    for td in soup.find_all('td'):
        if td.has_attr('mergewith'):
            abbr = td.get_text(strip=True)
            raw_full = td['mergewith']
            full = re.sub('<[^>]+>', ' ', raw_full)
            full = re.sub(r'\s+', ' ', full).strip()
            if not abbr or not full:
                continue
            if len(full) > len(abbr) + 3 and ' ' in full:
                subject_map.setdefault(abbr, full)
                if len(abbr) > 3 and abbr[-1] in {'c', 'w', 'L', 'S', 'E', 'l', 'C'}:
                    core = abbr[:-1]
                    subject_map.setdefault(core, full)
    # Text lines (dash / colon / double spaces)
    for raw_line in full_text.split('\n'):
        line = raw_line.strip()
        if not line or len(line) < 4:
            continue
        m = LEGEND_LINE_RE.match(line)
        if m:
            abbr = m.group('abbr').strip()
            full = m.group('full').strip()
            if len(full) > len(abbr) + 3 and ' ' in full:
                subject_map.setdefault(abbr, full)
                continue
        if '  ' in line:
            parts = re.split(r'\s{2,}', line, maxsplit=1)
            if len(parts) == 2:
                abbr, full = parts[0].strip(), parts[1].strip()
                if (abbr and full and len(full) > len(abbr) + 3 and ' ' in full and
                        re.match(r'^[A-Za-zĄąĆćĘęŁłŃńÓóŚśŹźŻż0-9]{1,15}$', abbr)):
                    subject_map.setdefault(abbr, full)
                    continue
        tokens = line.split()
        if 2 <= len(tokens) <= 12:
            abbr, rest = tokens[0], ' '.join(tokens[1:])
            if (3 <= len(rest) <= 100 and len(rest) > len(abbr) + 3 and ' ' in rest and
                    re.match(r'^[A-Za-zĄąĆćĘęŁłŃńÓóŚśŹźŻż]{1,10}$', abbr) and rest[0].isupper() and not rest.endswith('.')):
                subject_map.setdefault(abbr, rest)
    # Other tables (besides main) – column layout
    for tbl in soup.find_all('table'):
        if schedule_table is not None and tbl is schedule_table:
            continue
        for tr in tbl.find_all('tr'):
            cells = tr.find_all('td')
            if len(cells) < 1:
                continue
            for idx, td in enumerate(cells):
                abbr = td.get_text(strip=True)
                if not abbr or len(abbr) > 15:
                    continue
                if td.has_attr('mergewith'):
                    raw_full = td['mergewith']
                    full = re.sub('<[^>]+>', ' ', raw_full)
                    full = re.sub(r'\s+', ' ', full).strip()
                    if (full and len(full) > len(abbr) + 3 and ' ' in full and
                            re.match(r'^[A-Za-zĄąĆćĘęŁłŃńÓóŚśŹźŻż0-9]+$', abbr)):
                        subject_map.setdefault(abbr, full)
                        if len(abbr) > 3 and abbr[-1] in {'c','w','L','S','E','l','C'}:
                            subject_map.setdefault(abbr[:-1], full)
                        continue
                if idx + 1 < len(cells):
                    full_candidate = ' '.join(cells[idx+1].stripped_strings).strip()
                    if (full_candidate and len(full_candidate) > len(abbr) + 3 and ' ' in full_candidate and
                            not full_candidate.endswith('.') and re.match(r'^[A-Za-zĄąĆćĘęŁłŃńÓóŚśŹźŻż0-9]+$', abbr)):
                        subject_map.setdefault(abbr, full_candidate)
                        if len(abbr) > 3 and abbr[-1] in {'c','w','L','S','E','l','C'}:
                            subject_map.setdefault(abbr[:-1], full_candidate)
    return subject_map


# Scrapes WTC groups from the WAT website.
async def fetch_schedule_html(context, url: str, group: str, idx: int, total: int):
    page = await context.new_page()
    logs = []
    try:
        await page.goto(url, timeout=15000)
        await page.wait_for_load_state('domcontentloaded')
        html = await page.content()
        log_entry(f"Scraping group ({idx}/{total}) | {group} Done.", logs)
        return html
    except Exception as e:
        log_entry(f"{W} Fail ({idx}/{total}) {group}: {e}", logs)
        return None
    finally:
        await page.close()


# Parses the WTC table from the HTML content.
def parse_wtc_table(html: str, employees_map: dict):
    if not html:
        return []
    soup = BeautifulSoup(html, 'html.parser')
    table = soup.find('table')
    if not table:
        tables = soup.find_all('table')
        if not tables:
            return []
        table = tables[0]

    subject_legend = extract_legend_maps(soup, schedule_table=table)
    lecturer_legend = extract_lecturer_legend(soup)
    # Build index
    variant_index, employee_records = build_employee_code_index(employees_map)

    rows = table.find_all('tr')
    lessons = []
    current_day = None
    current_dates_for_day = []

    update_year = None
    m_upd = re.search(r'Data aktualizacji:\s*(\d{2})[./](\d{2})[./](\d{4})', soup.get_text())
    if m_upd:
        update_year = int(m_upd.group(3))
    else:
        update_year = datetime.now().year

    for tr in rows:
        cells = tr.find_all(['td', 'th'])
        if not cells:
            continue
        first = cells[0].get_text(strip=True)
        # Row with date headers
        if first in DAY_ALIASES and len(cells) > 2 and not cells[1].get_text(strip=True):
            current_day = first
            current_dates_for_day = []
            for c in cells[2:]:
                token = c.get_text(strip=True).replace('\xa0', ' ').strip()
                if not token:
                    current_dates_for_day.append(None)
                    continue
                m = DATE_TOKEN_RE.match(token)
                if m:
                    day_num = int(m.group(1))
                    roman = m.group(2)
                    month = ROMAN_MONTH.get(roman)
                    if month:
                        try:
                            dt = datetime(update_year, month, day_num)
                            current_dates_for_day.append(dt)
                        except ValueError:
                            current_dates_for_day.append(None)
                    else:
                        current_dates_for_day.append(None)
                else:
                    current_dates_for_day.append(None)
            continue
        # Rows with time blocks
        if first in DAY_ALIASES and len(cells) > 2:
            if not current_day:
                continue
            block_label = cells[1].get_text(strip=True)
            if block_label not in BLOCK_TIME_MAP:
                continue
            start_time, end_time = BLOCK_TIME_MAP[block_label]
            for i, c in enumerate(cells[2:]):
                if i >= len(current_dates_for_day):
                    break
                dt = current_dates_for_day[i]
                if not dt:
                    continue
                # Collect lines from <font> and <br>
                raw_lines = [t.strip() for t in c.stripped_strings if t.strip() and t.strip() != '-']
                if not raw_lines:
                    continue
                # First line is subject abbreviation (e.g. 'Psw', 'Tch', 'Fj', 'Swb')
                subject_abbr = raw_lines[0]
                # Look for type symbol (exact line in TYPE_SYMBOLS)
                symbol = ''
                room = ''
                lecturer_codes = []
                other_tokens = []
                for line in raw_lines[1:]:
                    # Single token type markers
                    if line in TYPE_SYMBOLS and not symbol:
                        symbol = line
                        continue
                    # Room detection: prefer first numeric token
                    room_match = re.match(r'^(\d{2,3}[A-Z]?)', line)
                    if room_match and not room:
                        room = room_match.group(1)
                        continue
                    # Lecturer codes pattern
                    if re.match(r'^[A-ZŻŹĆŁŚÓ][a-ząćęłńóśźżA-Z]{1,7}$', line) or re.match(r'^[A-Z][A-Za-z]{2,}$', line):
                        lecturer_codes.append(line)
                        continue
                    # Lines like '24 Trzc' – extract trailing code
                    m_last = re.search(r'([A-ZŻŹĆŁŚÓ][a-zA-Ząćęłńóśźż]{2,})$', line)
                    if m_last:
                        lecturer_codes.append(m_last.group(1))
                    other_tokens.append(line)
                full_subject_name = subject_legend.get(subject_abbr, subject_abbr)
                type_full = TYPE_FULL_MAP.get(symbol, symbol)
                # Lecturer mapping
                if not lecturer_codes and subject_abbr == 'WF':
                    # Fallback for physical education (often missing short code)
                    czajko_key = next((k for k in employees_map.values() if 'Czajko' in k), None)
                    if czajko_key:
                        lecturer_codes.append('Czajko')
                lecturers_full = resolve_lecturer_names(lecturer_codes, variant_index, employee_records, LECTURER_NAME_MODE, legend_map=lecturer_legend)
                lesson = {
                    'date': dt.strftime('%Y_%m_%d'),
                    'start': datetime.strptime(start_time, '%H:%M').replace(year=dt.year, month=dt.month, day=dt.day),
                    'end': datetime.strptime(end_time, '%H:%M').replace(year=dt.year, month=dt.month, day=dt.day),
                    'subject': subject_abbr,
                    'type': symbol,
                    'type_full': type_full,
                    'room': room,
                    'lesson_number': '',
                    'full_subject_name': full_subject_name,
                    'lecturers': lecturers_full,
                }
                lessons.append(lesson)
    # Lesson numbering per (subject, type)
    counter = {}
    totals = {}
    for les in lessons:
        key = (les['subject'], les['type'])
        totals[key] = totals.get(key, 0) + 1
    for les in lessons:
        key = (les['subject'], les['type'])
        counter[key] = counter.get(key, 0) + 1
        les['lesson_number'] = f"{counter[key]}/{totals[key]}"
    # Propagate lecturers for lessons missing them
    subj_type_lect = {}
    subj_any_lect = {}
    for les in lessons:
        if les.get('lecturers'):
            st_key = (les['subject'], les['type'])
            subj_type_lect.setdefault(st_key, set()).update(les['lecturers'])
            subj_any_lect.setdefault(les['subject'], set()).update(les['lecturers'])
    for les in lessons:
        if not les.get('lecturers'):
            st_key = (les['subject'], les['type'])
            cand = subj_type_lect.get(st_key) or subj_any_lect.get(les['subject'])
            if cand and len(cand) <= 3:
                les['lecturers'] = sorted(cand)
    return lessons


# Writes the lessons to an ICS file.
def write_ics(group: str, lessons: list):
    base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', 'db', OUTPUT_DIR_NAME)
    os.makedirs(base_dir, exist_ok=True)
    path = os.path.join(base_dir, f"{sanitize_filename(group)}.ics")
    with open(path, 'w', encoding='utf-8') as f:
        for line in ICS_HEADER:
            f.write(line + '\n')
        f.write(f"X-WR-CALNAME:{group}\n")
        for les in lessons:
            dtstart = les['start'].strftime('%Y%m%dT%H%M%S')
            dtend = les['end'].strftime('%Y%m%dT%H%M%S')
            summary = f"{les['subject']} ({les['type']})" if les['type'] else les['subject']
            description_lines = [
                (les.get('full_subject_name') or les['subject']),
                f"Type: {les['type_full']}",
                f"No: {les['lesson_number']}",
            ]
            if les.get('lecturers'):
                description_lines.append("Lecturer: " + "; ".join(les['lecturers']))
            f.write("BEGIN:VEVENT\n")
            f.write(f"DTSTART:{dtstart}\n")
            f.write(f"DTEND:{dtend}\n")
            f.write(f"SUMMARY:{summary}\n")
            if les.get('room'):
                f.write(f"LOCATION:{les['room']}\n")
            f.write(f"DESCRIPTION:{'\\n'.join(description_lines)}\n")
            f.write("END:VEVENT\n")
        f.write("END:VCALENDAR\n")
    return len(lessons)

# Wrapper to save all schedules in a single log operation
def save_all_wtc_calendars(schedules: dict):
    def do_all():
        logs = []
        saved_groups = 0
        for gid, lessons in schedules.items():
            if lessons:
                count = write_ics(gid, lessons)
                saved_groups += 1
            else:
                log_entry(f"{W} {gid}: no lessons parsed", logs)
        return saved_groups
    return log("Saving WTC schedules... ", do_all)

async def scrape_all_wtc(groups: list, base_pattern: str, employees: dict, concurrency: int = 8):
    results = {}
    semaphore = asyncio.Semaphore(concurrency)
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=[
            '--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage', '--disable-gpu'
        ])
        context = await browser.new_context(user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0 Safari/537.36")

        async def worker(gid, idx, total):
            async with semaphore:
                url = base_pattern.format(group=gid)
                html = await fetch_schedule_html(context, url, gid, idx, total)
                lessons = parse_wtc_table(html, employees)
                results[gid] = lessons

        tasks = [worker(g, i+1, len(groups)) for i, g in enumerate(groups)]
        await asyncio.gather(*tasks)
        await browser.close()
    return results

def run_async(title, coro, *args, **kwargs):
    def runner():
        return asyncio.run(coro(*args, **kwargs))
    return log(title, runner)

if __name__ == '__main__':
    start = time.time()
    print(f"{INFO} Start WTC schedules scraper {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    print(f"\n{INFO} Connection to WTC website with groups.")

    url_pattern, desc = load_url_from_config(category="schedules", faculty="wtc", url_type="url")
    from connection import test_connection_with_monitoring 
    test_connection_with_monitoring(url_pattern, desc)
    if not url_pattern:
        print(f"{E} No URL for schedules.")
        sys.exit(1)

    employees = load_employees()
    groups = load_groups('wtc')

    if not groups:
        print(f"{E} No WTC groups found.")
        sys.exit(1)

    schedules = run_async("Scraping WTC schedules... ", scrape_all_wtc, groups, url_pattern, employees, 8)
    saved_total = save_all_wtc_calendars(schedules)
    print(f"{OK} Saved schedules for {saved_total}/{len(groups)} groups.")
    print(f"{INFO} Finished in {time.time() - start:.2f}s")
