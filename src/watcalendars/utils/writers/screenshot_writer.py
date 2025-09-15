"""Screenshot writer utilities for saving page screenshots"""
import os
from watcalendars import SCHEDULES_DIR
from watcalendars.utils.config import sanitize_filename
from watcalendars.utils.logutils import log_entry, SUCCESS, WARNING, OK, ERROR

def get_target_dir(faculty_prefix=""):
    """Get target directory for screenshots"""
    if faculty_prefix:
        return os.path.join(SCHEDULES_DIR, f"{faculty_prefix}_schedules")
    return SCHEDULES_DIR

async def save_screenshot_async(page, group_id, faculty_prefix=""):
    """Save screenshot asynchronously (for async Playwright)"""
    target_dir = get_target_dir(faculty_prefix)
    os.makedirs(target_dir, exist_ok=True)

    filename = os.path.join(target_dir, f"{sanitize_filename(group_id)}.png")
    try:
        await page.screenshot(path=filename, full_page=True)
        if os.path.exists(filename):
            log_entry(f"{OK} Saved screenshot for {group_id}", [])
        else:
            log_entry(f"{ERROR} Failed to save screenshot for {group_id}", [])
    except Exception as e:
        log_entry(f"{ERROR} Failed to save screenshot for {group_id}: {e}", [])
    return filename
