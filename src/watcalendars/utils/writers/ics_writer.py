import os
from watcalendars import CALENDARS_DIR
from watcalendars.utils.config import sanitize_filename
from watcalendars.utils.logutils import log, log_entry, SUCCESS, WARNING, OK, ERROR

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
            
        dtstart = norm_lesson["start"].strftime("%Y%m%dT%H%M%S")
        dtend = norm_lesson["end"].strftime("%Y%m%dT%H%M%S")
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