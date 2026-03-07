import os
import json
from watcalendars.utils.url_loader import load_url_from_config
from watcalendars.utils.log import OK, ERROR, WARNING, INFO, SUCCESS

def save_groups_json(groups, groups_dir, filename_prefix, url_config_path, schedule_key, schedule_type, season_suffix=""):
    """
    Save group/url pairs in JSON file for given faculty.
    Args:
        groups: iterable of group tokens (str)
        groups_dir: directory for saving
        filename_prefix: 'ioe', 'wcy', etc. (makes ioe.json, wcy.json)
        url_config_path: path to url_for_schedules.json
        schedule_key: key in url_for_schedules.json (e.g. 'ioe_schedule')
        schedule_type: url type (e.g. 'url_lato')
        season_suffix: '_lato' or '_zima' to be added to the filename
    """

    def save_groups_json_log():
        logs = []
        
        # Create a subdirectory for the faculty if it doesn't exist
        faculty_groups_dir = os.path.join(groups_dir, f"{filename_prefix}_groups_url")
        if not os.path.exists(faculty_groups_dir):
            os.makedirs(faculty_groups_dir)
            
        filename = os.path.join(faculty_groups_dir, f"{filename_prefix}_groups{season_suffix}_url.json")
        logs.append(f"Making file for saving groups..."); print(f"Making file for saving groups...")
        url_template, _ = load_url_from_config(url_config_path, schedule_key, schedule_type)
        logs.append(f"Loading url for groups..."); print(f"Loading url for groups...")
        if not url_template:
            logs.append(f"{ERROR} Cannot get URL template for {schedule_key}/{schedule_type}"); print(f"{ERROR} Cannot get URL template for {schedule_key}/{schedule_type}")
            return

        groups_dict = {g: url_template.replace("{group}", g) for g in sorted(groups)}
        try:
            logs.append(f"Open file for writing..."); print(f"Open file for writing...")
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(groups_dict, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logs.append(f"{ERROR} Failed to save groups to {filename}: {e}"); print(f"{ERROR} Failed to save groups to {filename}: {e}")
        return groups_dict, filename, logs

    groups_dict, filename, logs = (print(f"{INFO} Saving groups..."), save_groups_json_log())[1]
    if os.path.exists(filename):
        logs.append(f"{SUCCESS} Saved {len(groups_dict)} {filename_prefix.upper()} group/url pairs to '{os.path.abspath(filename)}'."); print(f"{SUCCESS} Saved {len(groups_dict)} {filename_prefix.upper()} group/url pairs to '{os.path.abspath(filename)}'.")  
    else:
        logs.append(f"{ERROR} Failed to save {filename_prefix.upper()} groups to '{os.path.abspath(filename)}'."); print(f"{ERROR} Failed to save {filename_prefix.upper()} groups to '{os.path.abspath(filename)}'.")