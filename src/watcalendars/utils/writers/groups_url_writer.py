import os
import json
from watcalendars.utils.logutils import OK, ERROR, log, log_entry, SUCCESS
from watcalendars.utils.url_loader import load_url_from_config

def save_groups_json(groups, groups_dir, filename_prefix, url_config_path, schedule_key, schedule_type):
    """
    Save group/url pairs in JSON file for given faculty.
    Args:
        groups: iterable of group tokens (str)
        groups_dir: directory for saving
        filename_prefix: 'ioe', 'wcy', etc. (makes ioe.json, wcy.json)
        url_config_path: path to url_for_schedules.json
        schedule_key: key in url_for_schedules.json (e.g. 'ioe_schedule')
        schedule_type: url type (e.g. 'url_lato')
    """

    def save_groups_json_log():
        logs = []
        filename = os.path.join(groups_dir, f"{filename_prefix}_groups_url.json")
        log_entry(f"Making file for saving groups. ", logs)
        url_template, _ = load_url_from_config(url_config_path, schedule_key, schedule_type)
        log_entry(f"Loading url for groups.", logs)
        if not url_template:
            log_entry(f"{ERROR} Cannot get URL template for {schedule_key}/{schedule_type}", logs)
            return

        groups_dict = {g: url_template.replace("{group}", g) for g in sorted(groups)}
        try:
            log_entry(f"Open file for writing.", logs)
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(groups_dict, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"{ERROR} {e}")
        return groups_dict, filename, logs

    groups_dict, filename, logs = log("Saving groups...", save_groups_json_log)
    if os.path.exists(os.path.join(groups_dir, f"{filename_prefix}_groups_url.json")):
        log_entry(f"{SUCCESS} Saved {len(groups_dict)} {filename_prefix.upper()} group/url pairs to '{os.path.abspath(filename)}'.", logs)  
    else:
        log_entry(f"{ERROR} Failed to save {filename_prefix.upper()} groups to '{os.path.abspath(filename)}'.", logs)