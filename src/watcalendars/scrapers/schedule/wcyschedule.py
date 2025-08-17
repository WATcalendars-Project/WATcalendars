import sys
import os
import time
import re
import asyncio
from watcalendars import DB_DIR
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse, quote
from watcalendars.utils.connection import test_connection_with_monitoring 
from watcalendars.utils.logutils import OK, WARNING as W, ERROR as E, INFO, log_entry, log, start_spinner, log_parsing
from watcalendars.utils.url_loader import load_url_from_config
from watcalendars.utils.employees_loader import load_employees
from watcalendars.utils.groups_loader import load_groups
from watcalendars.utils.config import BLOCK_TIMES, TYPE_FULL_MAP, sanitize_filename
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from datetime import datetime
from collections import defaultdict


def get_wcy_group_urls():
    groups = load_groups("wcy")
    result = []
    def log_get_wcy_group_urls():
        for g in groups:
            url = base_url.format(group=quote(str(g), safe="*"))
            result.append((g, url))
        return result
    result = log("Getting WCY group URLs...", log_get_wcy_group_urls)
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
        browser = await p.chromium.launch(headless=True, args=[
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-infobars",
            "--disable-dev-shm-usage",
            "--disable-web-security",
            "--allow-insecure-localhost",
            "--ignore-certificate-errors",
            "--headless"
        ])
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


def parse_schedule(html, employees):
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")
    lessons = []
    lesson_counters = defaultdict(int)
    max_lessons_count = defaultdict(int)

    for lesson in soup.find_all("div", class_="lesson"):
        try:
            subject_element = lesson.find("span", class_="name")
            
            if not subject_element:
                continue
            
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

    for lesson in soup.find_all("div", class_="lesson"):
        try:
            date_str_el = lesson.find("span", class_="date")
            block_id_el = lesson.find("span", class_="block_id")

            if not date_str_el or not block_id_el:
                continue

            date_str = date_str_el.text.strip()
            block_id = block_id_el.text.strip()

            subject_element = lesson.find("span", class_="name")
            
            if not subject_element:
                continue
            
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
            lecturer_match = re.search(
                r"- \(.+\) - ((?:dr |prof\. |inż\. )?[A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+) ([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+)",
                full_subject_info,
            )

            if lecturer_match:
                first_name = lecturer_match.group(2)
                last_name = lecturer_match.group(1)
                key = f"{first_name} {last_name}"
                lecturer_with_title = employees.get(key, key)

            else:
                name_match = re.search(
                    r"- \(.+\) - ([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+ [A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+)",
                    full_subject_info,
                )

                if name_match:
                    key = name_match.group(1)
                    lecturer_with_title = employees.get(key, key)

            lesson_type_full = TYPE_FULL_MAP.get(lesson_type, lesson_type)

            try:
                date_obj = datetime.strptime(date_str, "%Y_%m_%d")

            except Exception:
                continue

            start_time, end_time = BLOCK_TIMES.get(block_id, ("00:00", "00:00"))
            start_datetime = datetime.strptime(start_time, "%H:%M").replace(
                year=date_obj.year, month=date_obj.month, day=date_obj.day
            )
            end_datetime = datetime.strptime(end_time, "%H:%M").replace(
                year=date_obj.year, month=date_obj.month, day=date_obj.day
            )

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


def parse_schedules(html_map):
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
            lessons = parse_schedule(html, employees)
            schedules[group_id] = lessons
            events_done += len(lessons)
            groups_done += 1
        return schedules
        
    schedules = log_parsing("Parsing events for WCY schedules", log_parse_schedule, progress_fn=progress)
    return schedules


def save_schedule_to_ICS(group_id, lessons):
    schedules_dir = os.path.join(DB_DIR, "WCY_schedules")

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
            summary = f"{lesson['subject']} {lesson['type']}"
            location = lesson['room']
            description_lines = [
                lesson['full_subject'],
                f"Rodzaj zajęć: {lesson['type_full']}",
                f"Numer zajęć: {lesson['lesson_number']}",
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


if __name__ == "__main__":
    start_time = time.time()
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] Start WCY schedule scraper:")

    url, description = load_url_from_config(key="wcy_groups", url_type="url")
    test_connection_with_monitoring(url, description)

    base_url, description = load_url_from_config(key="wcy_schedule", url_type="url")
    
    pairs = get_wcy_group_urls()
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
        schedules_dir = os.path.join(DB_DIR, "WCY_schedules")
        logs = [] 
        if not os.path.exists(schedules_dir):
            log_entry("Creating WCY schedules directory", logs)
            os.makedirs(schedules_dir)
        else:
            log_entry("Using existing WCY schedules directory", logs)
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

    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] WCY schedules scraper finished (duration: {HH_MM_SS})")