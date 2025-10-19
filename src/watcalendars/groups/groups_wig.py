import os
import time
import json
from datetime import datetime

from watcalendars import DB_DIR, GROUPS_DIR, GROUPS_CONFIG
from watcalendars.utils.logutils import OK, ERROR, SUCCESS, WARNING
from watcalendars.utils.connection import test_connection_with_monitoring
from watcalendars.utils.url_loader import load_url_from_config
from watcalendars.utils.scraper import scrape_html
from watcalendars.utils.parsers.groups_parsers.subcategory_parser_wig import parse_wig_subcategories
from watcalendars.utils.parsers.groups_parsers.groups_parser_wig import parse_wig_groups_from_subcategory
from watcalendars.utils.writers.subcategory_writer import save_subcategories_json

if __name__ == '__main__':
    start_time = time.time()
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] Start of WIG groups scraper:")
    print("")

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
        print(f"Scraping subcategories from URL:\n{url}")
        html, logs = scrape_html(url)
        print("")

        print(f"Parsing {len(html)} bytes of HTML:")
        subcategories = parse_wig_subcategories(html, logs)
        print(f"{SUCCESS} Collected {len(subcategories)} WIG subcategories.")
        print("")

        if subcategories:
            output_dir = os.path.join(GROUPS_DIR, "subcategory")
            save_subcategories_json(
                subcategories=subcategories,
                output_dir=output_dir,
                filename="wig_subcategory_url.json"
            )
            print("")
            
            print(f"{'='*80}")
            print(f"Starting to scrape groups from {len(subcategories)} subcategories...")
            print(f"{'='*80}")
            print("")
            
            all_groups = {}
            
            for idx, (subcategory_name, subcategory_url) in enumerate(subcategories.items(), 1):
                print(f"[{idx}/{len(subcategories)}] Processing: {subcategory_name}")
                print(f"    URL: {subcategory_url}")
                
                try:
                    sub_html, sub_logs = scrape_html(subcategory_url)
                    
                    groups = parse_wig_groups_from_subcategory(sub_html, sub_logs)
                    
                    if groups:
                        print(f"    {SUCCESS} Found {len(groups)} groups")
                        
                        for group_name, download_url in groups.items():
                            all_groups[group_name] = download_url
                        
                        print("")
                    else:
                        print(f"    {WARNING} No groups found in this subcategory")
                        print("")
                        
                except Exception as e:
                    print(f"    {ERROR} Failed to process subcategory: {e}")
                    print("")
                    continue
            
            print(f"{'='*80}")
            print(f"Saving groups to JSON...")
            print(f"{'='*80}")
            print("")
            
            groups_json_path = os.path.join(GROUPS_DIR, "wig_groups_url.json")
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
    print("")

    duration = time.time() - start_time
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] WIG groups scraper finished  |  duration: {duration:.2f}s")
