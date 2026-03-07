import os
import json
from watcalendars.utils.log import OK, ERROR, WARNING, INFO, SUCCESS

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
        logs.append(f"Ensuring output directory exists..."); print(f"Ensuring output directory exists...")
        
        full_path = os.path.join(output_dir, filename)
        logs.append(f"Preparing to save to file..."); print(f"Preparing to save to file...")
        
        try:
            logs.append(f"Opening file for writing..."); print(f"Opening file for writing...")
            with open(full_path, 'w', encoding='utf-8') as f:
                json.dump(subcategories, f, indent=2, ensure_ascii=False)
            logs.append(f"{OK} Saved {len(subcategories)} subcategory/url pairs."); print(f"{SUCCESS} Saved {len(subcategories)} subcategory/url pairs.")
        except Exception as e:
            logs.append(f"{ERROR} {e}"); print(f"{ERROR} {e}")
            raise
        
        return full_path, logs

    full_path, logs = (print(f"{INFO} Saving subcategories..."), save_subcategories_json_log())[1]
    
    if os.path.exists(full_path):
        logs.append(f"{SUCCESS} File successfully saved to '{os.path.abspath(full_path)}'."); print(f"{SUCCESS} File successfully saved to '{os.path.abspath(full_path)}'.")  
    else:
        logs.append(f"{ERROR} Failed to save file to '{os.path.abspath(full_path)}'."); print(f"{ERROR} Failed to save file to '{os.path.abspath(full_path)}'.")
    
    return full_path
