"""
WTC-specific schedule parser with legend extraction and complex parsing logic.
"""

import re
import unicodedata
from datetime import datetime
from bs4 import BeautifulSoup
from watcalendars.utils.config import BLOCK_TIMES, ROMAN_MONTH, DATE_TOKEN_RE, TYPE_FULL_MAP, DAY_ALIASES, TYPE_SYMBOLS
from watcalendars.utils.employees_loader import load_employees
from watcalendars.utils.logutils import log_parsing, WARNING as W, log_entry, OK, ERROR, SUCCESS


def extract_legend(soup: BeautifulSoup) -> list[tuple[str, str, list[str]]]:
    """Extract subject legend with full names and lecturers from the HTML."""
    entries: list[tuple[str, str, list[str]]] = []
    seen: set[tuple[str, str]] = set()
    norm = lambda s: re.sub(r"\s+", " ", (s or "")).strip()
    is_lect = lambda t: re.search(r"(?i)\b(prof\.|dr|hab\.|mgr|inż\.|inz\.|ppłk|płk|mjr|kpt\.|por\.|ppor\.|chor\.|sierż\.|kpr\.)\b", t or "") is not None
    
    def split_lect(t: str) -> list[str]:
        parts = re.split(r"(?i)\s*(?:;|/|,| i | oraz )\s*", t)
        return [re.sub(r"^[•\-–]\s*", "", norm(p)) for p in parts if norm(p)]

    last_idx: int | None = None
    for td in soup.find_all("td"):
        full = None
        if td.has_attr("mergewith"):
            try:
                full = BeautifulSoup(td["mergewith"], "html.parser").get_text(" ", strip=True)
            except Exception:
                full = norm(re.sub(r"<[^>]+>", " ", td["mergewith"]))
        abbr = td.get_text(strip=True)
        lect_text = norm(full if full else " ".join(td.stripped_strings))
        if lect_text and is_lect(lect_text) and last_idx is not None:
            lects = entries[last_idx][2]
            for n in split_lect(lect_text):
                if n not in lects:
                    lects.append(n)
            if not (abbr and full):
                continue
        if full and abbr:
            key = (abbr, full)
            if key in seen:
                for idx in range(len(entries) - 1, -1, -1):
                    a, f, _ = entries[idx]
                    if a == abbr and f == full:
                        last_idx = idx
                        break
                continue
            seen.add(key)
            lects: list[str] = []
            entries.append((abbr, full, lects))
            last_idx = len(entries) - 1
    return entries


def normalize_type(sym: str) -> str:
    """Normalize lesson type symbol."""
    s = (sym or '').strip()
    if not s:
        return s
    if s in TYPE_SYMBOLS:
        return s
    core = s.strip('()')
    for cand in (f'({core})', f'({core.lower()})', f'({core.upper()})'):
        if cand in TYPE_SYMBOLS:
            return cand
    return s


def pick_lecturers_for_code(subj: str, code: str, subject_legend_lect: dict, all_lecturers: list) -> list[str]:
    """Pick appropriate lecturers for a subject code."""
    names = subject_legend_lect.get(subj) or []
    if not names:
        names = all_lecturers
    if not code:
        return names[:1] if len(names) == 1 else []

    if not names:
        return []

    def undiac(s: str) -> str:
        return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')

    codes = [c for c in re.split(r"[\s/,;]+", code.strip()) if c]
    result: list[str] = []
    seen: set[str] = set()
    norm_names = [(full, re.sub(r'[^a-z]', '', undiac(full).lower())) for full in names]
    for code_token in codes:
        k = re.sub(r'[^a-z]', '', undiac(code_token).lower())
        if not k:
            continue
        for full, hay in norm_names:
            if full in seen:
                continue
            if all(ch in hay for ch in set(k)):
                result.append(full)
                seen.add(full)
                break
    return result


def parse_schedule(html: str) -> list[dict]:
    """
    Parse WTC schedule HTML and extract lessons.
    
    Args:
        html: Raw HTML content
        
    Returns:
        List of lesson dictionaries with normalized data
    """
    if not html:
        return []

    soup = BeautifulSoup(html, 'html.parser')
    table = soup.find('table') or (soup.find_all('table')[0] if soup.find_all('table') else None)
    if not table:
        return []

    txt = re.sub(r"\s+", " ", soup.get_text(" ").strip())
    now = datetime.now()
    year = now.year
    m_year = re.search(r"(20\d{2})\s*/\s*(20\d{2})", txt)
    if m_year:
        y1, y2 = int(m_year.group(1)), int(m_year.group(2))
        year = y1 if now.month >= 9 else y2
    else:
        m_any = re.search(r"(20\d{2})", txt)
        if m_any:
            year = int(m_any.group(1))

    legend_entries = extract_legend(soup)
    subject_legend_full: dict[str, str] = {}
    subject_legend_lect: dict[str, list[str]] = {}
    all_lecturers: list[str] = []
    
    for abbr, full, lecturers in legend_entries:
        if abbr and full:
            subject_legend_full.setdefault(abbr, full)
            if lecturers:
                lst = subject_legend_lect.setdefault(abbr, [])
                for l in lecturers:
                    if l not in lst:
                        lst.append(l)
                        if l not in all_lecturers:
                            all_lecturers.append(l)

    lessons: list[dict] = []
    current_day = None
    current_dates: list[datetime | None] = []
    
    for tr in table.find_all('tr'):
        cells = tr.find_all(['td', 'th'])
        if not cells:
            continue
        first = (cells[0].get_text(strip=True) or '').lower()

        if first in DAY_ALIASES and len(cells) > 2 and not cells[1].get_text(strip=True):
            current_day = first
            current_dates = []
            for c in cells[2:]:
                token = (c.get_text(strip=True) or '').replace('\xa0', ' ').strip()
                if not token:
                    current_dates.append(None)
                    continue
                m = DATE_TOKEN_RE.match(token)
                if m:
                    d = int(m.group(1))
                    roman = m.group(2)
                    month = ROMAN_MONTH.get(roman)
                    if month:
                        try:
                            current_dates.append(datetime(year, month, d))
                        except ValueError:
                            current_dates.append(None)
                        continue
                current_dates.append(None)
            continue

        if first in DAY_ALIASES and len(cells) > 2 and current_day:
            block_label = cells[1].get_text(strip=True)
            if block_label not in BLOCK_TIMES:
                continue
            start_time, end_time = BLOCK_TIMES[block_label]
            
            for i, c in enumerate(cells[2:]):
                if i >= len(current_dates):
                    break
                dt = current_dates[i]
                if not dt:
                    continue
                    
                raw_lines = [t.strip() for t in c.stripped_strings if t.strip() and t.strip() != '-']
                if not raw_lines:
                    continue
                
                subject_abbr = raw_lines[0]
                if subject_abbr.strip().upper() == 'SK':
                    continue
                
                subj_norm = subject_abbr.strip().upper()
                if subj_norm.startswith('WF'):
                    type_token = raw_lines[1] if len(raw_lines) > 1 else ''
                    lect_code = raw_lines[2] if len(raw_lines) > 2 else ''
                    room = ''
                else:
                    type_token = raw_lines[1] if len(raw_lines) > 1 else ''
                    room = raw_lines[2] if len(raw_lines) > 2 else ''
                    lect_code = raw_lines[3] if len(raw_lines) > 3 else ''
                
                lesson_type = normalize_type(type_token)
                type_full = TYPE_FULL_MAP.get(lesson_type, lesson_type or '-')
                lecturers = pick_lecturers_for_code(subject_abbr, lect_code, subject_legend_lect, all_lecturers)
                full_subject_name = subject_legend_full.get(subject_abbr, subject_abbr)
                
                try:
                    start_dt = datetime.strptime(start_time, '%H:%M').replace(year=dt.year, month=dt.month, day=dt.day)
                    end_dt = datetime.strptime(end_time, '%H:%M').replace(year=dt.year, month=dt.month, day=dt.day)
                except Exception:
                    continue

                lessons.append({
                    'date': dt.strftime('%Y_%m_%d'),
                    'start': start_dt,
                    'end': end_dt,
                    'subject': subject_abbr,
                    'subject_display': subject_abbr,
                    'type': lesson_type,
                    'type_full': type_full,
                    'room': room,
                    'lesson_number': '',
                    'full_subject_name': full_subject_name,
                    'lecturers': lecturers,
                })

    totals: dict[tuple[str, str], int] = {}
    for les in lessons:
        key = (les['subject'], les['type'])
        totals[key] = totals.get(key, 0) + 1

    counters: dict[tuple[str, str], int] = {}
    for les in lessons:
        key = (les['subject'], les['type'])
        counters[key] = counters.get(key, 0) + 1
        les['lesson_number'] = f"{counters[key]}/{totals.get(key, 0)}"

    return lessons


def parse_schedules(html_map):
    """Parse multiple WTC schedule HTMLs"""
    employees = load_employees()
    schedules = {}
    total_groups = len(html_map)
    groups_done = 0
    events_done = 0

    def progress():
        return f"({groups_done}/{total_groups})"

    def log_parse_schedule():
        nonlocal groups_done, events_done
        for group_id, html in html_map.items():
            lessons = parse_schedule(html)
            schedules[group_id] = lessons
            log_entry(f"Parsing {group_id} completed.")
            events_done += len(lessons)
            groups_done += 1
        return schedules
        
    schedules = log_parsing("Parsing schedules", log_parse_schedule, progress_fn=progress)
    parsed_total = sum(len(lessons or []) for lessons in schedules.values())
    if parsed_total > 0:
        print(f"{SUCCESS} Summary: Parsed events: {parsed_total} across {len(schedules)} groups")
    else:
        print(f"{ERROR} No events parsed.")
    return schedules
