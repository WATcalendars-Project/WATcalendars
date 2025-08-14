#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import time
import re
import asyncio
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

# Align sys.path handling with wcygroups.py (add two levels up -> watcalendars package dir)
PARENT_WAT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PARENT_WAT_DIR not in sys.path:
    sys.path.insert(0, PARENT_WAT_DIR)

# Use short imports (module files sit in watcalendars dir now on sys.path)
from groups_loader import load_groups
from logutils import OK, WARNING as W, ERROR as E, INFO, log_entry, log
from url_loader import load_url_from_config
from employees_loader import load_employees
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from datetime import datetime
from collections import defaultdict

# definition of block times
BLOCK_TIMES = {
    "block1": ("08:00", "09:35"),
    "block2": ("09:50", "11:25"),
    "block3": ("11:40", "13:15"),
    "block4": ("13:30", "15:05"),
    "block5": ("16:00", "17:35"),
    "block6": ("17:50", "19:25"),
    "block7": ("19:40", "21:15"),
}

def sanitize_filename(filename):
    return re.sub(r'[<>:"\\|?*]', "_", filename)

# Helper to build group url
def build_group_url(base_url: str, group_id: str) -> str:
    parsed = urlparse(base_url)
    qs = parse_qs(parsed.query)
    qs["grupa_id"] = [str(group_id)]
    new_query = urlencode(qs, doseq=True)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment))

async def scrape_group(page, group_id, idx, total, url):
    max_retries = 3
    retry_count = 0
    html = None
    logs = []
    while retry_count < max_retries:
        try:
            await page.goto(url, timeout=30000)
            await page.wait_for_load_state("networkidle", timeout=15000)
            html = await page.content()
            log_entry(f"Scraping group ({idx}/{total}) | {group_id} Done.", logs)
            break
        except Exception as e:
            retry_count += 1
            log_entry(f"{W} Retry {retry_count}/{max_retries} for group ({idx}/{total}) | {group_id}...", logs)
            if retry_count < max_retries:
                await asyncio.sleep(2)
            else:
                log_entry(f"{E} Failed to scrape group ({idx}/{total}) | {group_id} after {max_retries} attempts\n{e}", logs)
    return html

# Parse schedule html -> lessons list
def parse_schedule(html, employees):
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    lessons = []
    lesson_counters = defaultdict(int)
    max_lessons_count = defaultdict(int)
    # Pre-pass to detect max lesson numbers
    for lesson in soup.find_all("div", class_="lesson"):
        try:
            subject_element = lesson.find("span", class_="name")
            subject_lines = [line.strip() for line in subject_element.stripped_strings]
            if len(subject_lines) < 4:
                continue
            subject_short = subject_lines[0]
            lesson_type = subject_lines[1]
            lesson_number_match = re.search(r"\[(\d+)\]", subject_lines[3])
            lesson_number = int(lesson_number_match.group(1)) if lesson_number_match else 0
            lesson_key = (subject_short, lesson_type)
            if lesson_number:
                max_lessons_count[lesson_key] = max(max_lessons_count[lesson_key], lesson_number)
        except:
            continue
    # Detailed parse
    for lesson in soup.find_all("div", class_="lesson"):
        try:
            date_str_el = lesson.find("span", class_="date")
            block_id_el = lesson.find("span", class_="block_id")
            if not date_str_el or not block_id_el:
                continue
            date_str = date_str_el.text.strip()
            block_id = block_id_el.text.strip()
            subject_element = lesson.find("span", class_="name")
            subject_lines = [line.strip() for line in subject_element.stripped_strings]
            if len(subject_lines) < 4:
                continue
            subject_short = subject_lines[0]
            lesson_type = subject_lines[1]
            room = subject_lines[2].replace(",", "").strip()
            lesson_number_match = re.search(r"\[(\d+)\]", subject_lines[3])
            lesson_number = int(lesson_number_match.group(1)) if lesson_number_match else 0
            lesson_key = (subject_short, lesson_type)
            lesson_counters[lesson_key] += 1
            max_lessons = max_lessons_count.get(lesson_key) or lesson_number or 0
            lesson_number_formatted = f"{lesson_counters[lesson_key]}/{max_lessons or '?'}"
            info_element = lesson.find("span", class_="info")
            full_subject_info = info_element.text.strip() if info_element else " - "
            full_subject_cleaned = re.sub(r" - \(.+\) - .*", "", full_subject_info).strip()
            lecturer_with_title = "-"
            lecturer_match = re.search(r"- \(.+\) - ((?:dr |prof\. |inż\. )?[A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+) ([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+)", full_subject_info)
            if lecturer_match:
                first_name = lecturer_match.group(2)
                last_name = lecturer_match.group(1)
                key = f"{first_name} {last_name}"
                lecturer_with_title = employees.get(key, key)
            else:
                name_match = re.search(r"- \(.+\) - ([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+ [A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+)", full_subject_info)
                if name_match:
                    key = name_match.group(1)
                    lecturer_with_title = employees.get(key, key)
            lesson_type_full = {
                "(w)": "Wykład",
                "(L)": "Laboratorium",
                "(ć)": "Ćwiczenia",
                "(P)": "Projekt",
                "(inne)": "inne",
            }.get(lesson_type, lesson_type)
            try:
                date_obj = datetime.strptime(date_str, "%Y_%m_%d")
            except:
                continue
            start_time, end_time = BLOCK_TIMES.get(block_id, ("00:00", "00:00"))
            start_datetime = datetime.strptime(start_time, "%H:%M").replace(year=date_obj.year, month=date_obj.month, day=date_obj.day)
            end_datetime = datetime.strptime(end_time, "%H:%M").replace(year=date_obj.year, month=date_obj.month, day=date_obj.day)
            lessons.append({
                "date": date_str,
                "start": start_datetime,
                "end": end_datetime,
                "subject": subject_short,
                "type": lesson_type,
                "type_full": lesson_type_full,
                "room": room,
                "lesson_number": lesson_number_formatted,
                "full_subject": full_subject_cleaned,
                "lecturer": lecturer_with_title,
            })
        except Exception as e:
            print(f"{W} Error parsing lesson: {e}")
    return lessons

# Save lessons to ICS (no spinner per event / per file)
def save_schedule_to_file(group_id, lessons):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    db_dir = os.path.join(script_dir, "..", "..", "..", "db")
    schedules_dir = os.path.join(db_dir, "WCY_schedules")
    os.makedirs(schedules_dir, exist_ok=True)
    filename = os.path.join(schedules_dir, f"{sanitize_filename(group_id)}.ics")
    with open(filename, "w", encoding="utf-8") as f:
        f.write("BEGIN:VCALENDAR\n")
        f.write("VERSION:2.0\n")
        f.write("PRODID:-//scheduleWCY//EN\n")
        f.write("CALSCALE:GREGORIAN\n")
        f.write(f"X-WR-CALNAME:{group_id}\n")
        for lesson in lessons:
            dtstart = lesson['start'].strftime('%Y%m%dT%H%M%S')
            dtend = lesson['end'].strftime('%Y%m%dT%H%M%S')
            summary = f"{lesson['subject']} ({lesson['type']})"
            location = lesson['room']
            description_lines = [
                lesson['full_subject'],
                f"Rodzaj: {lesson['type_full']}",
                f"Nr: {lesson['lesson_number']}",
                f"Prowadzący: {lesson['lecturer']}"
            ]
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

def save_all_schedules_with_spinner(schedules):
    def do_save_all():
        saved = 0
        for gid, lessons in schedules.items():
            if lessons:
                try:
                    save_schedule_to_file(gid, lessons)
                    saved += 1
                except Exception as ex:
                    print(f"{E} Save failed for {gid}: {ex}")
            else:
                print(f"{W} No lessons for {gid}")
        return saved
    saved_total = log("Saving WCY schedules (all groups)... ", do_save_all)
    print(f"{OK} Saved {saved_total} ICS files.")
    return saved_total

# Async scrape many groups
async def scrape_all_schedules(groups, base_url, employees, concurrency=8):
    results = {}
    semaphore = asyncio.Semaphore(concurrency)
    start = time.time()
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=[
            '--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage', '--disable-gpu'
        ])
        context = await browser.new_context(user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0 Safari/537.36")
        async def worker(gid, idx, total):
            async with semaphore:
                page = await context.new_page()
                full_url = build_group_url(base_url, gid)
                html = await scrape_group(page, gid, idx, total, full_url)
                await page.close()
                lessons = parse_schedule(html, employees)
                results[gid] = lessons
        tasks = [worker(gid, i+1, len(groups)) for i, gid in enumerate(groups)]
        await asyncio.gather(*tasks)
        await browser.close()
    duration = time.time() - start
    print(f"{INFO} Scraped {len(groups)} groups in {duration:.2f}s")
    return results

# Wrapper to use spinner for async job
def run_async_with_spinner(title, coro_fn, *args, **kwargs):
    def wrapper():
        return asyncio.run(coro_fn(*args, **kwargs))
    return log(title, wrapper)

if __name__ == "__main__":
    start_time = time.time()
    print(f"{INFO} Start WCY schedule scraper {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    print(f"\n{INFO} Connection to WCY website with groups.")

    url, description = load_url_from_config(key="wcy_schedule", url_type="url")
    from connection import test_connection_with_monitoring 
    test_connection_with_monitoring(url, description)
    if not url:
        print(f"{E} No URL for schedules.")
        sys.exit(1)

    employees = load_employees()

    groups = load_groups("wcy")
    if not groups:
        print(f"{E} No groups found.")
        sys.exit(1)

    schedules = run_async_with_spinner("Scraping all schedules... ", scrape_all_schedules, groups, url, employees)
    save_all_schedules_with_spinner(schedules)
    print(f"{INFO} Finished {datetime.now().strftime('%Y-%m-%d %H:%M')}")