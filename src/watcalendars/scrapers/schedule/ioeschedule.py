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


def get_ioe_group_urls():
    groups = load_groups("ioe")
    result = []

    def log_get_ioe_group_urls():
        for g in groups:
            url = base_url.format(group=quote(str(g), safe="*"))
            result.append((g, url))
        return result

    result = log("Getting IOE group URLs...", log_get_ioe_group_urls)
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

    def norm(s: str | None) -> str:
        return re.sub(r"\s+", " ", (s or "")).strip()

    def is_lect(t: str) -> bool:
        pattern = r"(?i)\b(prof|dr|hab|mgr|inz|pplk|plk|mjr|kpt|por|ppor|chor|sierz|kpr)\.?\b"
        s = ''.join(c for c in unicodedata.normalize('NFD', t or '') if unicodedata.category(c) != 'Mn')
        s = s.replace('ł', 'l').replace('Ł', 'L')
        return re.search(pattern, s or "") is not None

    def split_lect(t: str) -> list[str]:
        parts = re.split(r"(?i)\s*(?:;|/|,| i | oraz |•|\n|\r)\s*", t)
        return [re.sub(r"^[•\-–]\s*", "", norm(p)) for p in parts if norm(p)]

    def is_abbr(token: str) -> bool:
        token = norm(token)
        if not token:
            return False
        return bool(re.fullmatch(r"[A-ZĄĆĘŁŃÓŚŹŻ]{2,6}\d?", token))

    def first_full_name_line(info_cell) -> str:
        lines = [norm(s) for s in info_cell.stripped_strings if norm(s)]
        for ln in lines:
            if is_lect(ln):
                continue
            if re.match(r"(?i)^(w|ć|l|s|e|z|zp)\.?\s*\d+", ln):
                continue
            if len(ln) >= 6 and " " in ln:
                return ln
        cand = ""
        for ln in lines:
            if not is_lect(ln) and not re.match(r"(?i)^(w|ć|l|s|e|z|zp)\.?\s*\d+", ln):
                if len(ln) > len(cand):
                    cand = ln
        return cand

    table = soup.find('table') or (soup.find_all('table')[0] if soup.find_all('table') else None)
    current: tuple[str, str, list[str]] | None = None
    if table:
        for tr in table.find_all('tr'):
            tds = tr.find_all('td')
            if len(tds) < 2:
                continue
            left = tds[-2]
            right = tds[-1]
            left_text = norm(left.get_text(" ", strip=True))
            right_text = norm(right.get_text(" ", strip=True))
            abbr_in_left = is_abbr(left_text)
            abbr_in_right = is_abbr(right_text)

            if abbr_in_left or abbr_in_right:
                abbr_token = left_text if abbr_in_left else right_text
                info_cell = right if abbr_in_left else right 
                full = first_full_name_line(info_cell)
                if not full:
                    full = first_full_name_line(left) or right_text or left_text
                if full and abbr_token:
                    key = (abbr_token, full)
                    if key not in seen:
                        if current and (current[0], current[1]) not in seen:
                            entries.append(current)
                            seen.add((current[0], current[1]))
                        current = (abbr_token, full, [])
                    else:
                        current = (abbr_token, full, [])
                else:
                    current = None
                if current:
                    for cell in (right, left):
                        for ln in [norm(s) for s in cell.stripped_strings if norm(s)]:
                            if is_lect(ln):
                                for n in split_lect(ln):
                                    if n and n not in current[2]:
                                        current[2].append(n)
                continue
            if current and not (abbr_in_left or abbr_in_right):
                if not current[1]:
                    cand = first_full_name_line(right) or first_full_name_line(left)
                    if cand:
                        current = (current[0], cand, current[2])
                for cell in (right, left):
                    for ln in [norm(s) for s in cell.stripped_strings if norm(s)]:
                        if is_lect(ln):
                            for n in split_lect(ln):
                                if n and n not in current[2]:
                                    current[2].append(n)
                continue
        if current and (current[0], current[1]) not in seen:
            entries.append(current)
            seen.add((current[0], current[1]))
    if not entries:
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

    def undiac_local(s: str) -> str:
        return ''.join(c for c in unicodedata.normalize('NFD', s or '') if unicodedata.category(c) != 'Mn')

    def is_lect_text(t: str) -> bool:
        pattern = r"(?i)\b(prof|dr|hab|mgr|inz|pplk|plk|mjr|kpt|por|ppor|chor|sierz|kpr)\.?\b"
        s = undiac_local(t).replace('ł', 'l').replace('Ł', 'L')
        return re.search(pattern, s or "") is not None

    for node in soup.find_all(['p', 'td', 'font']):
        text = " ".join([t for t in node.stripped_strings])
        if not text:
            continue
        # split cautiously to catch multi-lecturer lines
        for piece in re.split(r"(?i)\s*(?:;|/|,| i | oraz |•|\n|\r)\s*", text):
            piece = piece.strip()
            if not piece:
                continue
            if is_lect_text(piece):
                name = re.sub(r"^[•\-–]\s*", "", piece)
                if name and name not in all_lecturers:
                    all_lecturers.append(name)

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
        subject_only = bool(names)
        if not names:
            names = all_lecturers
        if not code:
            return list(names)

        if not names:
            return []

        def undiac(s: str) -> str:
            return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')

        codes = [c for c in re.split(r"[\s/,;]+", code.strip()) if c]
        result: list[str] = []
        seen: set[str] = set()
        norm_names = [(full, re.sub(r'[^a-z]', '', undiac(full).lower())) for full in names]
        norm_all = [(full, re.sub(r'[^a-z]', '', undiac(full).lower())) for full in all_lecturers]
        for code_token in codes:
            k = re.sub(r'[^a-z]', '', undiac(code_token).lower())
            if not k:
                continue
            matched = False
            for full, hay in norm_names:
                if full in seen:
                    continue
                if all(ch in hay for ch in set(k)):
                    result.append(full)
                    seen.add(full)
                    matched = True
                    break
            if subject_only and not matched:
                for full, hay in norm_all:
                    if full in seen:
                        continue
                    if all(ch in hay for ch in set(k)):
                        result.append(full)
                        seen.add(full)
                        matched = True
                        break
            if not matched:
                if code_token not in seen:
                    result.append(code_token)
                    seen.add(code_token)
        return result

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
                    d = int(m.group(1)); roman = m.group(2)
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
                lecturers = pick_lecturers_for_code(subject_abbr, lect_code)
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

    schedules = log_parsing("Parsing events for IOE schedules", log_parse_schedule, progress_fn=progress)
    return schedules


def save_schedule_to_ICS(group_id, lessons):
    schedules_dir = os.path.join(DB_DIR, "IOE_schedules")
    filename = os.path.join(schedules_dir, f"{sanitize_filename(group_id)}.ics")
    with open(filename, "w", encoding="utf-8") as f:
        f.write("BEGIN:VCALENDAR\n")
        f.write("VERSION:0.2.0\n")
        f.write("PRODID:-//scheduleIOE//EN\n")
        f.write("CALSCALE:GREGORIAN\n")
        f.write(f"X-WR-CALNAME:{group_id}\n")
        for les in lessons:
            dtstart = les["start"].strftime("%Y%m%dT%H%M%S")
            dtend = les["end"].strftime("%Y%m%dT%H%M%S")
            summary = f"{les['subject']} {les['type']}"
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
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] Start IOE schedule scraper:")
    url, description = load_url_from_config(key="ioe_groups", url_type="url_lato")
    test_connection_with_monitoring(url, description)
    base_url, description = load_url_from_config(key="ioe_schedule", url_type="url_lato")
    pairs = get_ioe_group_urls()
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
        schedules_dir = os.path.join(DB_DIR, "IOE_schedules")
        logs = []
        if not os.path.exists(schedules_dir):
            log_entry("Creating IOE schedules directory", logs)
            os.makedirs(schedules_dir)
        else:
            log_entry("Using existing IOE schedules directory", logs)
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
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] IOE schedules scraper finished (duration: {HH_MM_SS})")