import sys
import os
import time
import re
import asyncio
import unicodedata
from watcalendars import DB_DIR
from urllib.parse import quote
from watcalendars.utils.connection import test_connection_with_monitoring
from watcalendars.utils.logutils import OK, WARNING as W, ERROR as E, INFO, log_entry, log, start_spinner, log_parsing
from watcalendars.utils.url_loader import load_url_from_config
from watcalendars.utils.groups_loader import load_groups
from watcalendars.utils.config import BLOCK_TIMES, ROMAN_MONTH, DATE_TOKEN_RE, TYPE_FULL_MAP, DAY_ALIASES, TYPE_SYMBOLS, sanitize_filename
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from datetime import datetime
from collections import defaultdict


def get_wel_group_urls():
    groups = load_groups("wel")
    result = []

    def log_get_wel_group_urls():
        for g in groups:
            url = base_url.format(group=quote(str(g), safe="*"))
            result.append((g, url))
        return result

    result = log("Getting WEL group URLs...", log_get_wel_group_urls)
    return result


async def fetch_group_html(page, idx, total, g, url):
    max_retries = 3
    retry_count = 0
    html = None
    logs = []
    while retry_count < max_retries:
        try:
            await page.goto(url, timeout=30000)
            await page.wait_for_load_state("networkidle", timeout=15000)
            html = await page.content()
            log_entry(f"{OK} Scraping group {g} completed.", logs)
            break
        except Exception as e:
            retry_count += 1
            log_entry(f"{W} Retry {retry_count}/{max_retries} for group {g} ({idx}/{total})...", logs)
            if retry_count < max_retries:
                await asyncio.sleep(2)
            else:
                log_entry(f"{E} Failed to scrape group {g} ({idx}/{total}) after {max_retries} attempts\n{e}", logs)
    if html and retry_count > 0:
        log_entry(f"{OK} Scraping group {g} completed after {retry_count} retries.", logs)
    return html


async def scrape_group_urls(pairs, concurrency: int = 10):
    results = {}
    semaphore = asyncio.Semaphore(concurrency)
    done = 0
    done_lock = asyncio.Lock()
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-infobars",
                "--disable-dev-shm-usage",
                "--disable-web-security",
                "--allow-insecure-localhost",
                "--ignore-certificate-errors",
                "--headless",
            ],
        )
        context = await browser.new_context()
        stop_event, spinner_task = start_spinner("Scraping groups", len(pairs), lambda: done, interval=0.2)

        async def worker(idx_pair):
            nonlocal done
            idx, (g, url) = idx_pair
            async with semaphore:
                page = await context.new_page()
                try:
                    html = await fetch_group_html(page, idx + 1, len(pairs), g, url)
                    results[g] = html
                finally:
                    await page.close()
                    async with done_lock:
                        done += 1
        try:
            await asyncio.gather(*[worker(item) for item in enumerate(pairs)])
        finally:
            stop_event.set()
            await spinner_task
            await browser.close()
    return results


def extract_legend(soup: BeautifulSoup) -> list[tuple[str, str, list[str]]]:
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


def parse_schedule(html: str) -> list[dict]:
    if not html:
        return []

    soup = BeautifulSoup(html, 'html.parser')
    tables = soup.find_all('table')
    table = None
    if tables:
        for t in tables:
            for tr in t.find_all('tr'):
                tds = tr.find_all(['td', 'th'])
                if not tds:
                    continue
                first_cell = (tds[0].get_text(strip=True) or '').lower()
                if first_cell in DAY_ALIASES:
                    table = t
                    break
            if table:
                break
        if not table:
            table = tables[0]
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

    def normalize_type(sym: str) -> str:
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

    def pick_lecturers_for_code(subj: str, code: str) -> list[str]:
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

    lessons: list[dict] = []
    current_day = None
    current_dates: list[datetime | None] = []
    active_cells: list[tuple[list[str], int] | None] = []
    for tr in table.find_all('tr'):
        cells = tr.find_all(['td', 'th'])
        if not cells:
            continue
        first = (cells[0].get_text(strip=True) or '').lower()
        if first in DAY_ALIASES and len(cells) > 2:
            tentative_dates: list[datetime | None] = []
            matched_any_date = False
            last_date_idx = -1
            for idx, c in enumerate(cells[2:]):
                token = (c.get_text(strip=True) or '').replace('\xa0', ' ').strip()
                if not token:
                    tentative_dates.append(None)
                    continue
                m = DATE_TOKEN_RE.match(token)
                if m:
                    d = int(m.group(1)); roman = m.group(2)
                    month = ROMAN_MONTH.get(roman)
                    if month:
                        try:
                            tentative_dates.append(datetime(year, month, d))
                        except ValueError:
                            tentative_dates.append(None)
                        matched_any_date = True
                        last_date_idx = idx
                        continue
                tentative_dates.append(None)
            if matched_any_date:
                current_day = first
                if last_date_idx >= 0:
                    current_dates = tentative_dates[: last_date_idx + 1]
                else:
                    current_dates = tentative_dates
                active_cells = [None] * len(current_dates)
                continue
        if current_day and len(cells) > 2:
            block_label = None
            block_idx = None
            if first in BLOCK_TIMES:
                block_label = first
                block_idx = 0
            elif cells[1].get_text(strip=True) in BLOCK_TIMES:
                block_label = cells[1].get_text(strip=True)
                block_idx = 1
            if not block_label:
                continue
            start_time, end_time = BLOCK_TIMES[block_label]

            def append_lesson_if_valid(dt: datetime | None, raw_lines: list[str]):
                if not (dt and raw_lines):
                    return
                lines = [t for t in raw_lines if t]
                percent_token = None
                if lines and '%' in lines[0]:
                    percent_token = lines[0]
                    lines = lines[1:]
                subject_abbr = None
                subject_idx = None
                for i, tok in enumerate(lines):
                    tt = tok.strip()
                    if re.fullmatch(r"[A-ZĄĆĘŁŃÓŚŹŻ]{2,6}", tt):
                        subject_abbr = tt
                        subject_idx = i
                        break
                if not subject_abbr or subject_abbr.upper() == 'SK':
                    return
                subject_display = f"{percent_token} {subject_abbr}".strip() if percent_token else subject_abbr
                symbol = ''
                room = ''
                lecturer_codes: list[str] = []
                rest = lines[subject_idx + 1:] if subject_idx is not None else []
                for line in rest:
                    if not symbol and line in TYPE_SYMBOLS:
                        symbol = line
                        continue
                    m_room = re.match(r'^(\d{2,3}(?:\s*\d{2})?[A-Z]?)$', line)
                    if not room and m_room:
                        room = m_room.group(1).replace(' ', '')
                        continue
                    if re.match(r'^[A-ZŻŹĆŁŚÓ]{2,}$', line) or re.match(r'^[A-ZŻŹĆŁŚÓ][a-ząćęłńóśźż]{2,}$', line):
                        lecturer_codes.append(line)
                        continue
                lesson_type = normalize_type(symbol)
                type_full = TYPE_FULL_MAP.get(lesson_type, lesson_type or '-')
                lect_code = ' '.join(lecturer_codes)
                lecturers = pick_lecturers_for_code(subject_abbr, lect_code)
                full_subject_name = subject_legend_full.get(subject_abbr, subject_abbr)
                try:
                    start_dt = datetime.strptime(start_time, '%H:%M').replace(year=dt.year, month=dt.month, day=dt.day)
                    end_dt = datetime.strptime(end_time, '%H:%M').replace(year=dt.year, month=dt.month, day=dt.day)
                except Exception:
                    return
                lessons.append({
                    'date': dt.strftime('%Y_%m_%d'),
                    'start': start_dt,
                    'end': end_dt,
                    'subject': subject_abbr,
                    'subject_display': subject_display,
                    'type': lesson_type,
                    'type_full': type_full,
                    'room': room,
                    'lesson_number': '',
                    'full_subject_name': full_subject_name,
                    'lecturers': lecturers,
                })
            col_idx = 0
            ci = block_idx + 1
            while col_idx < len(current_dates):
                if active_cells and col_idx < len(active_cells) and active_cells[col_idx]:
                    raw_lines, remaining = active_cells[col_idx]
                    remaining -= 1
                    active_cells[col_idx] = (raw_lines, remaining) if remaining > 0 else None
                    dt = current_dates[col_idx]
                    append_lesson_if_valid(dt, raw_lines)
                    col_idx += 1
                    continue
                if ci >= len(cells):
                    col_idx += 1
                    continue
                c = cells[ci]
                ci += 1
                try:
                    colspan = int(c.get('colspan') or 1)
                except Exception:
                    colspan = 1
                try:
                    rowspan = int(c.get('rowspan') or 1)
                except Exception:
                    rowspan = 1
                raw_lines = [t.strip() for t in c.stripped_strings if t.strip() and t.strip() != '-']
                for k in range(colspan):
                    if col_idx >= len(current_dates):
                        break
                    dt = current_dates[col_idx]
                    if rowspan > 1 and raw_lines and active_cells and col_idx < len(active_cells):
                        active_cells[col_idx] = (raw_lines, rowspan - 1)
                    append_lesson_if_valid(dt, raw_lines)
                    col_idx += 1
    return lessons

    
def parse_schedules(html_map):
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
            events_done += len(lessons)
            groups_done += 1
        return schedules

    schedules = log_parsing("Parsing events for WEL schedules", log_parse_schedule, progress_fn=progress)
    return schedules


def save_schedule_to_ICS(group_id, lessons):
    schedules_dir = os.path.join(DB_DIR, "WEL_schedules")
    filename = os.path.join(schedules_dir, f"{sanitize_filename(group_id)}.ics")
    with open(filename, "w", encoding="utf-8") as f:
        f.write("BEGIN:VCALENDAR\n")
        f.write("VERSION:2.0\n")
        f.write("PRODID:-//scheduleWEL//EN\n")
        f.write("CALSCALE:GREGORIAN\n")
        f.write(f"X-WR-CALNAME:{group_id}\n")
        for les in lessons:
            dtstart = les["start"].strftime("%Y%m%dT%H%M%S")
            dtend = les["end"].strftime("%Y%m%dT%H%M%S")
            summary_subject = les.get('subject_display', les.get('subject', ''))
            summary = f"{summary_subject} {les['type']}"
            location = les.get("room", "")
            description_lines = [
                les.get("full_subject_name", les.get("subject", "")),
                f"Rodzaj zajęć: {les['type_full']}",
                f"Numer zajęć: {les['lesson_number']}",
            ]
            if les.get("lecturers"):
                description_lines.append("Prowadzący: " + "; ".join(les["lecturers"]))
            description = "\\n".join(description_lines)
            f.write("BEGIN:VEVENT\n")
            f.write(f"DTSTART:{dtstart}\n")
            f.write(f"DTEND:{dtend}\n")
            f.write(f"SUMMARY:{summary}\n")
            f.write(f"LOCATION:{location}\n")
            f.write(f"DESCRIPTION:{description}\n")
            f.write("END:VEVENT\n")
        f.write("END:VCALENDAR\n")
    return True


if __name__ == "__main__":
    start_time = time.time()
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] Start WEL schedule scraper:")
    url, description = load_url_from_config(key="wel_groups", url_type="url_lato")
    test_connection_with_monitoring(url, description)
    base_url, description = load_url_from_config(key="wel_schedule", url_type="url_lato")
    pairs = get_wel_group_urls()
    if not pairs:
        print(f"{E} No groups found.")
        sys.exit(1)
    print("Scraping group URLs:")
    print(f"URL: {base_url}")
    html_map = asyncio.run(scrape_group_urls(pairs))
    schedules = parse_schedules(html_map)
    parsed_total = sum(len(lessons or []) for lessons in schedules.values())
    print(f"Parsed events: {parsed_total} across {len(schedules)} groups")

    def save_all_schedules():
        schedules_dir = os.path.join(DB_DIR, "WEL_schedules")
        logs = []
        if not os.path.exists(schedules_dir):
            log_entry("Creating WEL schedules directory", logs)
            os.makedirs(schedules_dir)
        else:
            log_entry("Using existing WEL schedules directory", logs)
        saved = 0
        for g, _ in pairs:
            lessons = schedules.get(g) or []
            save_schedule_to_ICS(g, lessons)
            saved += 1
    log(f"Saving all schedules to ICS files... ", save_all_schedules)

    duration = time.time() - start_time
    total_seconds = int(duration)
    hours, rem = divmod(total_seconds, 3600)
    minutes, seconds = divmod(rem, 60)
    if hours > 0:
        HH_MM_SS = f"{hours:02}h{minutes:02}m{seconds:02}s"
    elif minutes > 0:
        HH_MM_SS = f"{minutes:02}m{seconds:02}s"
    else:
        HH_MM_SS = f"{seconds:02}s"
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] WEL schedules scraper finished (duration: {HH_MM_SS})")