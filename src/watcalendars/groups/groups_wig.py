import os
import time
import json
import unicodedata
from datetime import datetime

from watcalendars import DB_DIR, GROUPS_DIR, GROUPS_CONFIG
from watcalendars.utils.connection import test_connection_with_monitoring
from watcalendars.utils.url_loader import load_url_from_config
from watcalendars.utils.scraper import scrape_html
from watcalendars.utils.parsers.groups_parsers.subcategory_parser_wig import parse_wig_subcategories
from watcalendars.utils.parsers.groups_parsers.groups_parser_wig import parse_wig_groups_from_subcategory
from watcalendars.utils.writers.subcategory_writer import save_subcategories_json
from watcalendars.utils.log import OK, ERROR, WARNING, INFO, SUCCESS

if __name__ == '__main__':
    start_time = time.time()
    print(f"\n------[{datetime.now().strftime('%Y-%m-%d %H:%M')}] Start of WIG groups scraper:------\n")

    url, description = load_url_from_config(
        config_file=GROUPS_CONFIG,
        key="wig_groups",
        url_type="url_podkategoria"
    )
    
    if not url:
        print(f"{ERROR} Failed to load URL from config.")
        exit(1)
    
    test_connection_with_monitoring(url, description)
    print("")

    try:
        print(f"{INFO} Scraping subcategories from URL:\n{url}")
        html, logs = scrape_html(url)
        print("")

        print(f"{INFO} Parsing {len(html)} bytes of HTML:")
        subcategories = parse_wig_subcategories(html, logs)
        print(f"{SUCCESS} Collected {len(subcategories)} WIG subcategories.")
        print("")

        if subcategories:
            output_dir = os.path.join(GROUPS_DIR, "wig_groups_url", "subcategory")
            save_subcategories_json(
                subcategories=subcategories,
                output_dir=output_dir,
                filename="wig_subcategory_url.json"
            )
            print("")
            
            print(f"{INFO} Starting to scrape groups from {len(subcategories)} subcategories...")
            
            all_groups = {}
            groups_by_subcategory = {}
            
            for idx, (subcategory_name, subcategory_url) in enumerate(subcategories.items(), 1):
                print(f"\033[96m[{idx}/{len(subcategories)}]\033[0m Processing: {subcategory_name}")
                
                try:
                    sub_html, sub_logs = scrape_html(subcategory_url)
                    
                    groups = parse_wig_groups_from_subcategory(sub_html, sub_logs)
                    
                    if groups:
                        print(f"{SUCCESS} Found {len(groups)} groups")
                        
                        groups_by_subcategory[subcategory_name] = groups
                        
                        for group_name, download_url in groups.items():
                            all_groups[group_name] = download_url
                        
                        print("")
                    else:
                        print(f"{WARNING} No groups found in this subcategory")
                        print("")
                        
                except Exception as e:
                    print(f"{ERROR} Failed to process subcategory: {e}")
                    print("")
                    continue
            
            print(f"Saving groups to JSON...")

            wig_groups_dir = os.path.join(GROUPS_DIR, "wig_groups_url", "wig_groups_by_subcategory")
            if not os.path.exists(wig_groups_dir):
                os.makedirs(wig_groups_dir)

            for subcategory_name, groups in groups_by_subcategory.items():
                safe_filename = unicodedata.normalize('NFKD', subcategory_name).encode('ASCII', 'ignore').decode('utf-8')
                safe_filename = "".join(c for c in safe_filename if c.isalnum() or c in (' ', '_')).rstrip()
                safe_filename = safe_filename.replace(' ', '_') + "_url.json"
                
                subcategory_json_path = os.path.join(wig_groups_dir, safe_filename)
                with open(subcategory_json_path, 'w', encoding='utf-8') as f:
                    json.dump(groups, f, indent=2, ensure_ascii=False)
                print(f"{OK} Saved {len(groups)} groups for subcategory '{subcategory_name}' to:\n'{subcategory_json_path}'")

            print("")
                        
            groups_json_path = os.path.join(GROUPS_DIR, "wig_groups_url", "wig_groups_url.json")
            with open(groups_json_path, 'w', encoding='utf-8') as f:
                json.dump(all_groups, f, indent=2, ensure_ascii=False)
            
            print(f"{SUCCESS} Saved {len(all_groups)} groups to '{groups_json_path}'")
            print("")
            
        else:
            print(f"{ERROR} No subcategories to process.")
            
    except Exception as e:
        print(f"{ERROR} {e}")
        import traceback
        traceback.print_exc()

    duration = time.time() - start_time
    print(f"{INFO} {datetime.now().strftime('%Y-%m-%d %H:%M')} WIG groups scraper finished  |  duration: {duration:.2f}s")
    print("")
