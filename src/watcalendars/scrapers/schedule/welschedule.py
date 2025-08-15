#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys, os, re, asyncio, time, unicodedata
from datetime import datetime
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from groups_loader import load_groups
from logutils import OK, WARNING as W, ERROR as E, INFO, log, log_entry
from url_loader import load_url_from_config
from employees_loader import load_employees

DAY_ALIASES={'pon.':'MON','wt.':'TUE','śr.':'WED','sr.':'WED','czw.':'THU','pt.':'FRI','sob.':'SAT','niedz.':'SUN'}
BLOCK_TIME_MAP={'1-2':("08:00","09:35"),'3-4':("09:50","11:25"),'5-6':("11:40","13:15"),'7-8':("13:30","15:05"),'9-10':("16:00","17:35"),'11-12':("17:50","19:25"),'13-14':("19:40","21:15")}
ROMAN_MONTH={'I':1,'II':2,'III':3,'IV':4,'V':5,'VI':6,'VII':7,'VIII':8,'IX':9,'X':10,'XI':11,'XII':12}
DATE_TOKEN_RE=re.compile(r'^(\d{2})\s+([IVX]{1,4})$')
TYPE_FULL_MAP={'w':'Lecture','W':'Lecture','ć':'Exercises','c':'Exercises','L':'Laboratory','lab':'Laboratory','S':'Seminar','E':'Exam','Ep':'Retake exam'}
TYPE_SYMBOLS=set(TYPE_FULL_MAP.keys())
LECTURER_NAME_MODE='always_full'
ICS_HEADER=["BEGIN:VCALENDAR","VERSION:2.0","PRODID:-//scheduleWEL//EN","CALSCALE:GREGORIAN"]
OUTPUT_DIR_NAME="WEL_schedules"

sanitize_filename=lambda s: re.sub(r'[<>:"\\|?*]','_',s)
_strip_diacritic=lambda s: ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c)!='Mn')

TITLE_PATTERN=re.compile(r"^(?:prof\.?\s*(?:dr\s*hab\.)?|dr\s*hab\.|dr\.|mgr\.?|inż\.?|mgr\s*inż\.|lic\.|hab\.|płk\.|ppłk\.|mjr\.|kpt\.|por\.|ppor\.|doc\.|st\.|mł\.)\s+", re.IGNORECASE)
EXTRA_TITLE_SEQ=re.compile(r"^(?:prof\.?\s*WAT)\s+", re.IGNORECASE)
NAME_TOKEN=re.compile(r'^[A-ZŻŹĆŁŚÓ][a-ząćęłńóśźżA-Z]{2,}$')
LECTURER_LINE_RE=re.compile(r'^([A-ZŻŹĆŁŚÓ][A-Za-zŻŹĆŁŚÓąćęłńóśźż]{2,12})\s+(.+)$')
TITLE_KEYWORDS=re.compile(r'(prof\.|dr|hab\.|mgr|inż\.|inż|lic\.|płk|ppłk|mjr|kpt|por|ppor)', re.IGNORECASE)
LEGEND_LINE_RE=re.compile(r'^(?P<abbr>[A-Za-zĄąĆćĘęŁłŃńÓóŚśŹźŻż0-9]{1,15})\s*[–\-:\u2013]\s+(?P<full>.+)$')

# Helpers

def _strip_titles(line:str)->str:
    s=line.strip(); prev=None
    while s and prev!=s:
        prev=s; s=EXTRA_TITLE_SEQ.sub('',s).strip(); s=TITLE_PATTERN.sub('',s).strip()
    return s

def build_employee_code_index(employees_map:dict):
    variant_index, records = {}, []
    for full in employees_map.values():
        clean_full=' '.join(full.split()); short=_strip_titles(clean_full); parts=short.split()
        if len(parts)<2: continue
        first,surname=parts[0],parts[-1]
        base_surname=_strip_diacritic(re.sub(r'[^A-Za-zĄąĆćĘęŁłŃńÓóŚśŹźŻż]','',surname)); base_first=_strip_diacritic(first)
        if not base_surname: continue
        variants={base_surname.lower(), base_surname[:4].lower(), base_surname[:5].lower()}
        if base_first:
            variants.update({(base_surname[:3]+base_first[0]).lower(), (base_first[0]+base_surname).lower(), (base_first[0]+base_surname[:4]).lower(), (base_surname[:2]+base_first[0]).lower(), (base_surname[:2]+base_first[:2]).lower(), (base_surname[:3]+base_first[:2]).lower()})
        rec={'full':clean_full,'short':short,'surname':base_surname.lower()}; records.append(rec)
        for v in variants: variant_index.setdefault(v, {'full':clean_full,'short':short})
    return variant_index, records

def _normalize_titles_spacing(txt:str)->str:
    txt=re.sub(r'\.(?=\S)','. ',txt); return re.sub(r'\s+',' ',txt).strip()

def extract_lecturer_legend(soup:BeautifulSoup):
    legend={}
    for raw in soup.get_text('\n').split('\n'):
        line=raw.strip();
        if 3<=len(line)<=160:
            m=LECTURER_LINE_RE.match(line)
            if m:
                code,rest=m.group(1),_normalize_titles_spacing(m.group(2).strip())
                tokens=rest.split(); cap=[t for t in tokens if NAME_TOKEN.match(t)]
                if len(cap)>=2 and (TITLE_KEYWORDS.search(rest) or len(cap)>=3): legend.setdefault(code,rest)
    for td in soup.find_all('td'):
        if td.has_attr('mergewith'):
            code=td.get_text(strip=True)
            if code and len(code)<=6:
                full_plain=_normalize_titles_spacing(re.sub('<[^>]+>',' ',td['mergewith']))
                if TITLE_KEYWORDS.search(full_plain):
                    cap=[t for t in full_plain.split() if NAME_TOKEN.match(t)]
                    if len(cap)>=2: legend.setdefault(code, full_plain)
    return legend

def extract_legend_maps(soup:BeautifulSoup, schedule_table=None):
    subject_map={}; full_text=soup.get_text('\n')
    for td in soup.find_all('td'):
        if td.has_attr('mergewith'):
            abbr=td.get_text(strip=True); raw_full=td['mergewith']
            full=re.sub('<[^>]+>',' ',raw_full); full=re.sub(r'\s+',' ',full).strip()
            if abbr and full and len(full)>len(abbr)+3 and ' ' in full:
                subject_map.setdefault(abbr,full)
                if len(abbr)>3 and abbr[-1] in {'c','w','L','S','E','l','C'}: subject_map.setdefault(abbr[:-1],full)
    for raw_line in full_text.split('\n'):
        line=raw_line.strip()
        if not line or len(line)<4: continue
        m=LEGEND_LINE_RE.match(line)
        if m:
            abbr=m.group('abbr').strip(); full=m.group('full').strip()
            if len(full)>len(abbr)+3 and ' ' in full:
                subject_map.setdefault(abbr,full); continue
        if '  ' in line:
            parts=re.split(r'\s{2,}', line, maxsplit=1)
            if len(parts)==2:
                abbr,full=parts[0].strip(),parts[1].strip()
                if abbr and full and len(full)>len(abbr)+3 and ' ' in full and re.match(r'^[A-Za-zĄąĆćĘęŁłŃńÓóŚśŹźŻż0-9]{1,15}$', abbr):
                    subject_map.setdefault(abbr,full); continue
        tokens=line.split()
        if 2<=len(tokens)<=12:
            abbr,rest=tokens[0],' '.join(tokens[1:])
            if 3<=len(rest)<=100 and len(rest)>len(abbr)+3 and ' ' in rest and re.match(r'^[A-Za-zĄąĆćĘęŁłŃńÓóŚśŹźŻż]{1,10}$', abbr) and rest[0].isupper() and not rest.endswith('.'):
                subject_map.setdefault(abbr,rest)
    for tbl in soup.find_all('table'):
        if schedule_table is not None and tbl is schedule_table: continue
        for tr in tbl.find_all('tr'):
            cells=tr.find_all('td')
            for idx,td in enumerate(cells):
                abbr=td.get_text(strip=True)
                if not abbr or len(abbr)>15: continue
                if td.has_attr('mergewith'):
                    full=_normalize_titles_spacing(re.sub('<[^>]+>',' ',td['mergewith']))
                    if full and len(full)>len(abbr)+3 and ' ' in full and re.match(r'^[A-Za-zĄąĆćĘęŁłŃńÓóŚśŹźŻż0-9]+$', abbr):
                        subject_map.setdefault(abbr,full)
                        if len(abbr)>3 and abbr[-1] in {'c','w','L','S','E','l','C'}: subject_map.setdefault(abbr[:-1],full)
                        continue
                if idx+1 < len(cells):
                    full_candidate=' '.join(cells[idx+1].stripped_strings).strip()
                    if full_candidate and len(full_candidate)>len(abbr)+3 and ' ' in full_candidate and not full_candidate.endswith('.') and re.match(r'^[A-Za-zĄąĆćĘęŁłŃńÓóŚśŹźŻż0-9]+$', abbr):
                        subject_map.setdefault(abbr,full_candidate)
                        if len(abbr)>3 and abbr[-1] in {'c','w','L','S','E','l','C'}: subject_map.setdefault(abbr[:-1],full_candidate)
    return subject_map

# Parser (WTC style)

def parse_wtc_table(html:str, employees_map:dict):
    if not html: return []
    soup=BeautifulSoup(html,'html.parser')
    table=soup.find('table') or (soup.find_all('table')[0] if soup.find_all('table') else None)
    if not table: return []
    subject_legend=extract_legend_maps(soup, schedule_table=table)
    lecturer_legend=extract_lecturer_legend(soup)
    variant_index, employee_records = build_employee_code_index(employees_map)
    lessons=[]; current_dates=[]
    m_upd=re.search(r'Data aktualizacji:\s*(\d{2})[./](\d{2})[./](\d{4})', soup.get_text())
    update_year=int(m_upd.group(3)) if m_upd else datetime.now().year
    for tr in table.find_all('tr'):
        cells=tr.find_all(['td','th'])
        if not cells: continue
        first=cells[0].get_text(strip=True)
        if first in DAY_ALIASES and len(cells)>2 and not cells[1].get_text(strip=True):
            current_dates=[]
            for c in cells[2:]:
                token=c.get_text(strip=True).replace('\xa0',' ').strip()
                if not token: current_dates.append(None); continue
                m=DATE_TOKEN_RE.match(token)
                if m:
                    day_num=int(m.group(1)); roman=m.group(2); month=ROMAN_MONTH.get(roman)
                    if month:
                        try: current_dates.append(datetime(update_year, month, day_num))
                        except ValueError: current_dates.append(None)
                    else: current_dates.append(None)
                else: current_dates.append(None)
            continue
        if first in DAY_ALIASES and len(cells)>2:
            block_label=cells[1].get_text(strip=True)
            if block_label not in BLOCK_TIME_MAP: continue
            start_time,end_time=BLOCK_TIME_MAP[block_label]
            for i,c in enumerate(cells[2:]):
                if i>=len(current_dates): break
                dt=current_dates[i]
                if not dt: continue
                raw_lines=[t.strip() for t in c.stripped_strings if t.strip() and t.strip()!='-']
                if not raw_lines: continue
                subject_abbr=raw_lines[0]
                symbol=''; room=''; lecturer_codes=[]
                for line in raw_lines[1:]:
                    if line in TYPE_SYMBOLS and not symbol: symbol=line; continue
                    m_room=re.match(r'^(\d{2,3}[A-Z]?)', line)
                    if m_room and not room: room=m_room.group(1); continue
                    if re.match(r'^[A-ZŻŹĆŁŚÓ][a-ząćęłńóśźżA-Z]{1,7}$', line) or re.match(r'^[A-Z][A-Zaż]{2,}$', line): lecturer_codes.append(line); continue
                    m_last=re.search(r'([A-ZŻŹĆŁŚÓ][a-zA-Ząćęłńóśźż]{2,})$', line)
                    if m_last: lecturer_codes.append(m_last.group(1))
                full_subject_name=subject_legend.get(subject_abbr, subject_abbr)
                type_full=TYPE_FULL_MAP.get(symbol, symbol)
                if not lecturer_codes and subject_abbr=='WF':
                    cz=next((k for k in employees_map.values() if 'Czajko' in k), None)
                    if cz: lecturer_codes.append('Czajko')
                lecturers_full=resolve_lecturer_names(lecturer_codes, variant_index, employee_records, LECTURER_NAME_MODE, legend_map=lecturer_legend)
                lessons.append({'date': dt.strftime('%Y_%m_%d'),'start': datetime.strptime(start_time,'%H:%M').replace(year=dt.year,month=dt.month,day=dt.day),'end': datetime.strptime(end_time,'%H:%M').replace(year=dt.year,month=dt.month,day=dt.day),'subject': subject_abbr,'type': symbol,'type_full': type_full,'room': room,'lesson_number': '','full_subject_name': full_subject_name,'lecturers': lecturers_full})
    counter={}; totals={}
    for les in lessons:
        k=(les['subject'], les['type']); totals[k]=totals.get(k,0)+1
    for les in lessons:
        k=(les['subject'], les['type']); counter[k]=counter.get(k,0)+1; les['lesson_number']=f"{counter[k]}/{totals[k]}"
    subj_type_lect={}; subj_any_lect={}
    for les in lessons:
        if les.get('lecturers'):
            st=(les['subject'], les['type'])
            subj_type_lect.setdefault(st,set()).update(les['lecturers'])
            subj_any_lect.setdefault(les['subject'],set()).update(les['lecturers'])
    for les in lessons:
        if not les.get('lecturers'):
            st=(les['subject'], les['type'])
            cand=subj_type_lect.get(st) or subj_any_lect.get(les['subject'])
            if cand and len(cand)<=3: les['lecturers']=sorted(cand)
    return lessons

# Specialized WEL parser (day row followed by multiple block rows without repeating day label)

def parse_wel_table(html:str, employees_map:dict):
    if not html: return []
    soup=BeautifulSoup(html,'html.parser')
    table=soup.find('table') or (soup.find_all('table')[0] if soup.find_all('table') else None)
    if not table: return []
    subject_legend=extract_legend_maps(soup, schedule_table=table)
    lecturer_legend=extract_lecturer_legend(soup)
    variant_index, employee_records = build_employee_code_index(employees_map)
    lessons=[]; current_dates=[]; current_day=None
    m_upd=re.search(r'Data aktualizacji:\s*(\d{2})[./](\d{2})[./](\d{4})', soup.get_text())
    update_year=int(m_upd.group(3)) if m_upd else datetime.now().year
    for tr in table.find_all('tr'):
        cells=tr.find_all(['td','th'])
        if not cells: continue
        first=cells[0].get_text(strip=True)
        # Day header row: day + empty cell + dates
        if first in DAY_ALIASES and len(cells)>2 and (len(cells)==0 or not cells[1].get_text(strip=True) or cells[1].get_text(strip=True) not in BLOCK_TIME_MAP):
            current_day=first
            current_dates=[]
            # Dates start after second cell
            for c in cells[2:]:
                token=c.get_text(strip=True).replace('\xa0',' ').strip()
                if not token: current_dates.append(None); continue
                m=DATE_TOKEN_RE.match(token)
                if m:
                    day_num=int(m.group(1)); roman=m.group(2); month=ROMAN_MONTH.get(roman)
                    if month:
                        try: current_dates.append(datetime(update_year, month, day_num))
                        except ValueError: current_dates.append(None)
                    else: current_dates.append(None)
                else:
                    current_dates.append(None)
            continue
        # Block row for current day: first cell is block number
        if current_day and first in BLOCK_TIME_MAP:
            block_label=first
            start_time,end_time=BLOCK_TIME_MAP[block_label]
            # Data cells start at index 2 if second cell empty, else 1
            start_idx=2 if len(cells)>1 and not cells[1].get_text(strip=True) else 1
            date_cells=cells[start_idx:start_idx+len(current_dates)] if current_dates else []
            for i,c in enumerate(date_cells):
                if i>=len(current_dates): break
                dt=current_dates[i]
                if not dt: continue
                raw_lines=[t.strip() for t in c.stripped_strings if t.strip() and t.strip()!='-']
                if not raw_lines: continue
                subject_abbr=raw_lines[0]
                symbol=''; room=''; lecturer_codes=[]
                for line in raw_lines[1:]:
                    if line in TYPE_SYMBOLS and not symbol: symbol=line; continue
                    m_room=re.match(r'^(\d{2,3}[A-Z]?)', line)
                    if m_room and not room: room=m_room.group(1); continue
                    if re.match(r'^[A-ZŻŹĆŁŚÓ][a-ząćęłńóśźżA-Z]{1,7}$', line) or re.match(r'^[A-Z][A-Zaż]{2,}$', line): lecturer_codes.append(line); continue
                    m_last=re.search(r'([A-ZŻŹĆŁŚÓ][a-zA-Ząćęłńóśźż]{2,})$', line)
                    if m_last: lecturer_codes.append(m_last.group(1))
                full_subject_name=subject_legend.get(subject_abbr, subject_abbr)
                type_full=TYPE_FULL_MAP.get(symbol, symbol)
                if not lecturer_codes and subject_abbr=='WF':
                    cz=next((k for k in employees_map.values() if 'Czajko' in k), None)
                    if cz: lecturer_codes.append('Czajko')
                lecturers_full=resolve_lecturer_names(lecturer_codes, variant_index, employee_records, LECTURER_NAME_MODE, legend_map=lecturer_legend)
                lessons.append({'date': dt.strftime('%Y_%m_%d'),'start': datetime.strptime(start_time,'%H:%M').replace(year=dt.year,month=dt.month,day=dt.day),'end': datetime.strptime(end_time,'%H:%M').replace(year=dt.year,month=dt.month,day=dt.day),'subject': subject_abbr,'type': symbol,'type_full': type_full,'room': room,'lesson_number': '','full_subject_name': full_subject_name,'lecturers': lecturers_full})
        # If a new day label appears mid-way (fails earlier heuristic), reset day
        elif first in DAY_ALIASES:
            current_day=first
            current_dates=[]
    # Post-process numbering & lecturer propagation
    counter={}; totals={}
    for les in lessons:
        k=(les['subject'], les['type']); totals[k]=totals.get(k,0)+1
    for les in lessons:
        k=(les['subject'], les['type']); counter[k]=counter.get(k,0)+1; les['lesson_number']=f"{counter[k]}/{totals[k]}"
    subj_type_lect={}; subj_any_lect={}
    for les in lessons:
        if les.get('lecturers'):
            st=(les['subject'], les['type'])
            subj_type_lect.setdefault(st,set()).update(les['lecturers'])
            subj_any_lect.setdefault(les['subject'],set()).update(les['lecturers'])
    for les in lessons:
        if not les.get('lecturers'):
            st=(les['subject'], les['type'])
            cand=subj_type_lect.get(st) or subj_any_lect.get(les['subject'])
            if cand and len(cand)<=3: les['lecturers']=sorted(cand)
    return lessons

# Lecturer resolver (after alias)

def resolve_lecturer_names(codes, variant_index, records, mode, legend_map=None):
    resolved=[]; legend_map=legend_map or {}
    for raw in codes:
        original_raw=raw; key=_strip_diacritic(raw).lower(); found=None
        legend_full=legend_map.get(raw)
        if legend_full: resolved.append({'full':legend_full,'short':_strip_titles(legend_full)}); continue
        found=variant_index.get(key)
        if not found:
            for k2 in (key[:5], key[:4], key[:3]):
                if k2 in variant_index: found=variant_index[k2]; break
        if not found and re.match(r'^[A-Za-zżźćńółęąśŻŹĆŁŚÓĘĄ]{2,3}[A-Z]$', raw):
            surname_part=key[:-1]; fi=key[-1]
            for rec in records:
                if rec['surname'].startswith(surname_part) and _strip_diacritic(rec['short'].split()[0])[0].lower()==fi.lower():
                    found={'full':rec['full'],'short':rec['short']}; break
        if not found and len(key)==2:
            cand=[rec for rec in records if rec['surname'].startswith(key)]
            if len(cand)==1:
                c=cand[0]; found={'full':c['full'],'short':c['short']}
        if not found:
            for rec in records:
                if rec['surname'].startswith(key[:3]): found={'full':rec['full'],'short':rec['short']}; break
        if not found:
            for code2,full_line in (legend_map or {}).items():
                if raw.lower() in full_line.lower().split():
                    found={'full':full_line,'short':_strip_titles(full_line)}; break
        if not found: found={'full':raw,'short':raw,'unresolved':original_raw}
        resolved.append(found)
    if mode=='always_full': return [r['full'] for r in resolved]
    if mode=='always_short': return [r['short'] for r in resolved]
    if any(r['full']==r['short'] for r in resolved): return [r['short'] for r in resolved]
    return [r['full'] for r in resolved]

# ICS writing

def write_ics(group:str, lessons:list):
    base_dir=os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','..','..','db',OUTPUT_DIR_NAME)
    os.makedirs(base_dir, exist_ok=True)
    path=os.path.join(base_dir,f"{sanitize_filename(group)}.ics")
    with open(path,'w',encoding='utf-8') as f:
        for line in ICS_HEADER: f.write(line+'\n')
        f.write(f"X-WR-CALNAME:{group}\n")
        for les in lessons:
            dtstart=les['start'].strftime('%Y%m%dT%H%M%S'); dtend=les['end'].strftime('%Y%m%dT%H%M%S')
            summary=f"{les['subject']} ({les['type']})" if les['type'] else les['subject']
            desc_lines=[(les.get('full_subject_name') or les['subject']), f"Type: {les['type_full']}", f"No: {les['lesson_number']}"]
            if les.get('lecturers'): desc_lines.append("Lecturer: "+"; ".join(les['lecturers']))
            f.write("BEGIN:VEVENT\n")
            f.write(f"DTSTART:{dtstart}\nDTEND:{dtend}\nSUMMARY:{summary}\n")
            if les.get('room'): f.write(f"LOCATION:{les['room']}\n")
            f.write(f"DESCRIPTION:{'\\n'.join(desc_lines)}\nEND:VEVENT\n")
        f.write("END:VCALENDAR\n")
    return len(lessons)

# Saving wrapper

def save_all_wel_calendars(schedules:dict):
    def do_all():
        logs=[]; saved=0
        for gid,lessons in schedules.items():
            if lessons: write_ics(gid, lessons); saved+=1
            else: log_entry(f"{W} {gid}: no lessons parsed", logs)
        return saved
    return log("Saving WEL schedules... ", do_all)

# Orchestration
async def scrape_all_wel(groups:list, base_pattern:str, employees:dict, concurrency:int=8):
    results={}; semaphore=asyncio.Semaphore(concurrency)
    async with async_playwright() as p:
        browser=await p.chromium.launch(headless=True, args=['--no-sandbox','--disable-setuid-sandbox','--disable-dev-shm-usage','--disable-gpu'])
        context=await browser.new_context(user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0 Safari/537.36")
        async def worker(gid, idx, total):
            async with semaphore:
                url=base_pattern.format(group=gid)
                html=await fetch_schedule_html(context, url, gid, idx, total)
                results[gid]=parse_wel_table(html, employees)
        await asyncio.gather(*[worker(g,i+1,len(groups)) for i,g in enumerate(groups)])
        await browser.close()
    return results

# Fetch reused
async def fetch_schedule_html(context, url, group, idx, total):
    page=await context.new_page(); logs=[]
    try:
        await page.goto(url, timeout=15000)
        await page.wait_for_load_state('domcontentloaded')
        html=await page.content(); log_entry(f"Scraping group ({idx}/{total}) | {group} Done.", logs); return html
    except Exception as e:
        log_entry(f"{W} Fail ({idx}/{total}) {group}: {e}", logs); return None
    finally:
        await page.close()

# Runner helper

def run_async(title, coro, *args, **kwargs):
    def runner(): return asyncio.run(coro(*args, **kwargs))
    return log(title, runner)

# Main
if __name__=='__main__':
    start=time.time()
    print(f"{INFO} Start WEL schedules scraper {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"\n{INFO} Connection to WEL website with schedules.")
    url_pattern, desc = load_url_from_config(key='wel_schedule', url_type='url_lato')
    from connection import test_connection_with_monitoring
    test_connection_with_monitoring(url_pattern, desc)
    if not url_pattern:
        print(f"{E} No URL for schedules."); sys.exit(1)
    employees=load_employees(); groups=load_groups('wel')
    if not groups:
        print(f"{E} No WEL groups found."); sys.exit(1)
    schedules=run_async("Scraping WEL schedules... ", scrape_all_wel, groups, url_pattern, employees, 8)
    saved=save_all_wel_calendars(schedules)
    print(f"{OK} Saved schedules for {saved}/{len(groups)} groups.")
    print(f"{INFO} Finished in {time.time()-start:.2f}s")
