#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""WTC schedules scraper.
Próba odwzorowania funkcjonalności wcyschedule.py dla struktury tabelarycznej WTC.
HTML WTC zawiera duże tabele: dla każdego dnia (pon., wt., ...) mamy:
 - wiersz z dniem i pustą kolumną bloków + listą dat ("03 III", "10 III" ...)
 - kolejne wiersze z tym samym dniem + numer bloków ("1-2", "3-4" ...) + zawartość dla każdej daty
 Każda niepusta komórka = zajęcia w danym dniu, w danym przedziale bloków, w konkretnej dacie kolumny.
Ten parser jest heurystyczny – może wymagać dopracowania po obejrzeniu pełnego HTML.
"""
import sys
import os
import re
import asyncio
import time
from datetime import datetime
from urllib.parse import urlparse

# Podobnie jak inne moduły – dodajemy katalog pakietu
PARENT_WAT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PARENT_WAT_DIR not in sys.path:
    sys.path.insert(0, PARENT_WAT_DIR)

from groups_loader import load_groups  # noqa: E402
from logutils import OK, WARNING as W, ERROR as E, INFO, log, log_entry  # noqa: E402
from url_loader import load_url_from_config  # noqa: E402
from employees_loader import load_employees  # noqa: E402
from playwright.async_api import async_playwright  # noqa: E402
from bs4 import BeautifulSoup  # noqa: E402

DAY_ALIASES = {
    'pon.': 'MON', 'wt.': 'TUE', 'śr.': 'WED', 'sr.': 'WED', 'czw.': 'THU', 'pt.': 'FRI', 'sob.': 'SAT', 'niedz.': 'SUN'
}

# Mapowanie bloków (przyjęte analogicznie jak w WCY – dopasuj jeśli inne)
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
DATE_TOKEN_RE = re.compile(r'^(\d{2})\s+([IVX]{1,4})$')  # np. 03 III

ICS_HEADER = [
    "BEGIN:VCALENDAR",
    "VERSION:2.0",
    "PRODID:-//scheduleWTC//EN",
    "CALSCALE:GREGORIAN",
]

OUTPUT_DIR_NAME = "WTC_schedules"

def sanitize_filename(filename: str) -> str:
    return re.sub(r'[<>:"\\|?*]', '_', filename)

async def fetch_schedule_html(context, url: str, group: str, idx: int, total: int):
    page = await context.new_page()
    logs = []
    try:
        await page.goto(url, timeout=15000)
        await page.wait_for_load_state('domcontentloaded')
        html = await page.content()
        log_entry(f"Fetched ({idx}/{total}) {group}", logs)
        return html
    except Exception as e:
        log_entry(f"{W} Fail ({idx}/{total}) {group}: {e}", logs)
        return None
    finally:
        await page.close()

def parse_wtc_table(html: str, employees_map: dict):
    if not html:
        return []
    soup = BeautifulSoup(html, 'html.parser')
    table = soup.find('table')
    if not table:
        # fallback – może więcej tabel, weź wszystkie
        tables = soup.find_all('table')
        if not tables:
            return []
        table = tables[0]

    rows = table.find_all('tr')
    lessons = []
    idx = 0
    current_day = None
    current_dates_for_day = []  # list of (date_str, dt)

    # Spróbuj wyciągnąć rok z "Data aktualizacji: dd.mm.yyyy" w całym HTML
    update_year = None
    m_upd = re.search(r'Data aktualizacji:\s*(\d{2})[./](\d{2})[./](\d{4})', soup.get_text())
    if m_upd:
        update_year = int(m_upd.group(3))
    else:
        update_year = datetime.utcnow().year

    for tr in rows:
        cells = tr.find_all(['td', 'th'])
        if not cells:
            continue
        first = cells[0].get_text(strip=True)
        # Wiersz dat dla dnia: ma day abbrev + drugi pusty + dalej daty
        if first in DAY_ALIASES and len(cells) > 2 and not cells[1].get_text(strip=True):
            current_day = first
            current_dates_for_day = []
            for c in cells[2:]:
                token = c.get_text(strip=True).replace('\xa0', ' ').strip()
                if not token:
                    current_dates_for_day.append(None)
                    continue
                # Formaty mogą być np. '03 III'
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
        # Wiersz bloków dla dnia
        if first in DAY_ALIASES and len(cells) > 2:
            if not current_day:
                continue  # brak dat
            block_label = cells[1].get_text(strip=True)
            # np. '1-2'
            if block_label not in BLOCK_TIME_MAP:
                continue
            start_time, end_time = BLOCK_TIME_MAP[block_label]
            # Reszta komórek dopasowana do current_dates_for_day
            for i, c in enumerate(cells[2:]):
                content = c.get_text(" ", strip=True)
                if not content or content == '-':
                    continue
                if i >= len(current_dates_for_day):
                    break
                dt = current_dates_for_day[i]
                if not dt:
                    continue
                # Parsowanie uproszczone: próba wyciągnięcia sali (np. '55A', '315'), typu zajęć (w / ć / lab) i skrótu
                room_match = re.search(r'\b(\d{2,3}[A-Z]?)\b', content)
                room = room_match.group(1) if room_match else ''
                # typ: 'w', 'ć', 'lab' / 'L'
                type_match = re.search(r'\b(w|ć|lab|L)\b', content)
                lesson_type = type_match.group(1) if type_match else ''
                subject = content.split()[0]
                # wykładowca często w ostatniej kolumnie w innym wierszu – ten parser może nie uchwycić.
                lecturer = ''
                lessons.append({
                    'date': dt.strftime('%Y_%m_%d'),
                    'start': datetime.strptime(start_time, '%H:%M').replace(year=dt.year, month=dt.month, day=dt.day),
                    'end': datetime.strptime(end_time, '%H:%M').replace(year=dt.year, month=dt.month, day=dt.day),
                    'subject': subject,
                    'type': lesson_type,
                    'type_full': lesson_type,
                    'room': room,
                    'lesson_number': '',
                    'full_subject': content,
                    'lecturer': lecturer,
                })
    return lessons

def write_ics(group: str, lessons: list):
    base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', 'db', OUTPUT_DIR_NAME)
    os.makedirs(base_dir, exist_ok=True)
    path = os.path.join(base_dir, f"{sanitize_filename(group)}.ics")
    def do_write():
        with open(path, 'w', encoding='utf-8') as f:
            for line in ICS_HEADER:
                f.write(line + '\n')
            f.write(f"X-WR-CALNAME:{group}\n")
            for les in lessons:
                dtstart = les['start'].strftime('%Y%m%dT%H%M%S')
                dtend = les['end'].strftime('%Y%m%dT%H%M%S')
                summary = f"{les['subject']} ({les['type']})" if les['type'] else les['subject']
                description_lines = [
                    les['full_subject'],
                    f"Typ: {les['type_full']}",
                    f"Nr: {les['lesson_number']}",
                ]
                if les['lecturer']:
                    description_lines.append(f"Prowadzący: {les['lecturer']}")
                f.write("BEGIN:VEVENT\n")
                f.write(f"DTSTART:{dtstart}\n")
                f.write(f"DTEND:{dtend}\n")
                f.write(f"SUMMARY:{summary}\n")
                if les['room']:
                    f.write(f"LOCATION:{les['room']}\n")
                f.write(f"DESCRIPTION:{'\\n'.join(description_lines)}\n")
                f.write("END:VEVENT\n")
            f.write("END:VCALENDAR\n")
        return len(lessons)
    count = log(f"Saving WTC {group} schedule... ", do_write)
    print(f"{OK} {group}: {count} events saved.")

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
    url_pattern, desc = load_url_from_config(category='schedules', faculty='wtc', url_type='url')
    if not url_pattern:
        print(f"{E} No WTC schedule URL pattern.")
        sys.exit(1)
    employees = load_employees()
    groups = load_groups('wtc')
    if not groups:
        print(f"{E} No WTC groups found.")
        sys.exit(1)
    # Test subset – odkomentuj jeśli trzeba
    # groups = groups[:5]
    schedules = run_async("Scraping WTC schedules... ", scrape_all_wtc, groups, url_pattern, employees, 8)
    saved_total = 0
    for gid, lessons in schedules.items():
        if lessons:
            write_ics(gid, lessons)
            saved_total += 1
        else:
            print(f"{W} {gid}: no lessons parsed")
    print(f"{OK} Saved schedules for {saved_total}/{len(groups)} groups.")
    print(f"{INFO} Finished in {time.time() - start:.2f}s")
