import os
import json
from watcalendars.utils.logutils import OK, ERROR, log, log_entry, SUCCESS

def save_subcategories_json(subcategories, output_dir, filename):
    """
    Save subcategory/url pairs in JSON file.
    Args:
        subcategories: dict of {subcategory_name: url}
        output_dir: directory for saving (e.g., db/groups_url/subcategory)
        filename: filename (e.g., 'wig_subcategory_url.json')
    """

    def save_subcategories_json_log():
        logs = []
        
        os.makedirs(output_dir, exist_ok=True)
        log_entry(f"Ensuring output directory exists: {output_dir}", logs)
        
        full_path = os.path.join(output_dir, filename)
        log_entry(f"Preparing to save to file: {full_path}", logs)
        
        try:
            log_entry(f"Opening file for writing.", logs)
            with open(full_path, 'w', encoding='utf-8') as f:
                json.dump(subcategories, f, indent=2, ensure_ascii=False)
            log_entry(f"{SUCCESS} Saved {len(subcategories)} subcategory/url pairs.", logs)
        except Exception as e:
            log_entry(f"{ERROR} {e}", logs)
            raise
        
        return full_path, logs

    full_path, logs = log("Saving subcategories...", save_subcategories_json_log)
    
    if os.path.exists(full_path):
        log_entry(f"{SUCCESS} File successfully saved to '{os.path.abspath(full_path)}'.", logs)  
    else:
        log_entry(f"{ERROR} Failed to save file to '{os.path.abspath(full_path)}'.", logs)
    
    return full_path
