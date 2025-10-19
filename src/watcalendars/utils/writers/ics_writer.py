import os
from datetime import datetime, timezone, timedelta
from watcalendars import CALENDARS_DIR
from watcalendars.utils.config import sanitize_filename
from watcalendars.utils.logutils import log, log_entry, SUCCESS, WARNING, OK, ERROR

def _last_sunday(year: int, month: int) -> int:
    """Return day-of-month for the last Sunday in given month/year."""
    if month == 12:
        next_month = datetime(year + 1, 1, 1)
    else:
        next_month = datetime(year, month + 1, 1)
    last = next_month - timedelta(days=1)
    return (last.day - ((last.weekday() + 1) % 7))

def _warsaw_utc_offset(dt_local_naive: datetime) -> timedelta:
    """Approximate Europe/Warsaw UTC offset without tzdata.
    Rules (current EU):
    - Standard time (CET, UTC+1): from last Sunday of October 03:00 local until last Sunday of March 02:00 UTC.
    - Daylight time (CEST, UTC+2): from last Sunday of March 02:00 local until last Sunday of October 03:00 local.
    """
    y = dt_local_naive.year
    mar_day = _last_sunday(y, 3)
    dst_start = datetime(y, 3, mar_day, 2, 0, 0)
    oct_day = _last_sunday(y, 10)
    dst_end = datetime(y, 10, oct_day, 3, 0, 0)
    if dst_start <= dt_local_naive < dst_end:
        return timedelta(hours=2)
    return timedelta(hours=1)

def _format_dt_utc(dt):
    """Return ICS datetime string in UTC with 'Z'. If dt is naive, assume Europe/Warsaw local time."""
    if dt is None:
        return ""
    if dt.tzinfo is None:
        offset = _warsaw_utc_offset(dt)
        utc_dt = dt - offset
    else:
        utc_dt = dt.astimezone(timezone.utc)
    return (utc_dt if isinstance(utc_dt, datetime) else dt).strftime("%Y%m%dT%H%M%SZ")

def get_target_dir(faculty_prefix=""):
    if faculty_prefix:
        return os.path.join(CALENDARS_DIR, f"{faculty_prefix}_calendars")
    return CALENDARS_DIR

def normalize_lesson_data(lesson):
    """Normalize lesson data to common format for different faculties"""
    normalized = {
        "start": lesson.get("start"),
        "end": lesson.get("end"),
        "subject": lesson.get("subject", ""),
        "type": lesson.get("type", ""),
        "type_full": lesson.get("type_full", lesson.get("type", "")),
        "room": lesson.get("room", lesson.get("location", "")),
        "lesson_number": lesson.get("lesson_number", ""),
        "full_subject": lesson.get("full_subject", lesson.get("full_subject_name", lesson.get("subject", ""))),
        "lecturer": lesson.get("lecturer", ""),
        "lecturers": lesson.get("lecturers", [])
    }
    
    if normalized["lecturer"] and not normalized["lecturers"]:
        normalized["lecturers"] = [normalized["lecturer"]]
    elif normalized["lecturers"] and not normalized["lecturer"]:
        normalized["lecturer"] = "; ".join(normalized["lecturers"])
    
    return normalized

def generate_ics_content(group_id, lessons):
    """Generate ICS content for any faculty with normalized data"""
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//WATcalendars//EN",
        "CALSCALE:GREGORIAN",
        f"X-WR-CALNAME:{group_id}",
    ]
    
    for lesson in lessons:
        norm_lesson = normalize_lesson_data(lesson)
        
        if not norm_lesson["start"] or not norm_lesson["end"]:
            continue  
            
        dtstart = _format_dt_utc(norm_lesson["start"]) 
        dtend = _format_dt_utc(norm_lesson["end"]) 
        summary = f"{norm_lesson['subject']} {norm_lesson['type']}"
        location = norm_lesson["room"]
        
        description_lines = []
        
        if norm_lesson["full_subject"]:
            description_lines.append(norm_lesson["full_subject"])
        
        if norm_lesson["type_full"]:
            description_lines.append(f"Rodzaj zajęć: {norm_lesson['type_full']}")
        
        if norm_lesson["lesson_number"]:
            description_lines.append(f"Numer zajęć: {norm_lesson['lesson_number']}")
        
        if norm_lesson["lecturers"]:
            description_lines.append("Prowadzący: " + "; ".join(norm_lesson["lecturers"]))
        elif norm_lesson["lecturer"]:
            description_lines.append(f"Prowadzący: {norm_lesson['lecturer']}")
        
        description = "\\n".join(description_lines)
        
        lines.extend([
            "BEGIN:VEVENT",
            f"DTSTART:{dtstart}",
            f"DTEND:{dtend}",
            f"SUMMARY:{summary}",
            f"LOCATION:{location}",
            f"DESCRIPTION:{description}",
            "END:VEVENT"
        ])
    
    lines.append("END:VCALENDAR")
    return "\n".join(lines)

def save_schedule_to_ICS(group_id, lessons, faculty_prefix=""):
    target_dir = get_target_dir(faculty_prefix)
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)
    filename = os.path.join(target_dir, f"{sanitize_filename(group_id)}.ics")
    ics_content = generate_ics_content(group_id, lessons)

    status = "added"
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            old_content = f.read()
        if old_content == ics_content:
            status = "unchanged"
        else:
            status = "changed"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(ics_content)
    return status

def save_all_schedules(schedules, pairs, faculty_prefix=""):
    print("Saving all schedules:")

    def save_and_log():
        target_dir = get_target_dir(faculty_prefix)
        if not os.path.exists(target_dir):
            log_entry(f"Create calendars directory '{target_dir}'", [])
            os.makedirs(target_dir)
        else:
            log_entry(f"Use existing calendars directory '{target_dir}'", [])

        summary = {"added": [], "changed": [], "unchanged": []}
        saved = 0
        for g, _ in pairs:
            lessons = schedules.get(g) or []
            if len(lessons) == 0:
                log_entry(f"{WARNING} No lessons found for {g}  |  Skipping", [])
                continue
            status = save_schedule_to_ICS(g, lessons, faculty_prefix)
            summary[status].append(g)
            if status == "added":
                log_entry(f"{SUCCESS} Finished saving {g}: {status}", [])
            elif status == "changed":
                log_entry(f"{WARNING} Finished saving {g}: {status}", [])
            else:
                log_entry(f"{OK} Finished saving {g}: {status}", [])
            saved += 1
        if saved > 0:
            log_entry(f"{SUCCESS} Summary: ICS files ({saved})", [])
            log_entry(f"added: {len(summary['added'])} changed: {len(summary['changed'])} unchanged: {len(summary['unchanged'])}", [])
        else:
            log_entry(f"{ERROR} No ICS files saved.", [])
        return saved

    return log("Saving ICS calendars...", save_and_log)