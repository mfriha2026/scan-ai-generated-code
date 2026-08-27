import json
import glob
import os
import subprocess
import sys
import re

def get_live_pr_status(repo, pr_num):
    """
    🎯 LIVE PR STATUS ENGINE: Queries the GitHub CLI live loop directly to resolve
    open, closed, or merged parameters natively without static lookups.
    """
    if not repo or not pr_num:
        return "🟣 Merged"
    try:
        cmd = f"gh pr view {pr_num} --repo {repo} --json state"
        sub_env = os.environ.copy()
        res = subprocess.run(cmd, capture_output=True, text=True, shell=True, timeout=15, env=sub_env)
        if res.returncode == 0:
            data = json.loads(res.stdout)
            raw_state = str(data.get('state', 'CLOSED')).strip().upper()
            if raw_state == "MERGED":
                return "🟣 Merged"
            elif raw_state == "OPEN":
                return "🟢 Open"
            else:
                return "🔴 Closed"
    except Exception:
        pass
    return "🟣 Merged"

def main():
    matrix_str = os.environ.get('MATRIX_JSON', '{}')
    scan_type = os.environ.get('SCAN_TYPE', 'automated').lower().strip()
    
    # Extract the chunk offset pointer from the workflow environment variables
    try:
        chunk_offset = int(os.environ.get('CHUNK_OFFSET', '0'))
    except (ValueError, TypeError):
        chunk_offset = 0
        
    table_rows = []
    
    # Direct single source of truth mapping!
    is_human_run = (scan_type == 'human')

    # Separate database targets to match workflow requirements perfectly
    if is_human_run:
        accumulated_db_path = "all-results/human_accumulated_database.json"
        print("📁 [DATABASE TARGET]: Strict human tracking track detected. Targeting human ledger.")
    else:
        accumulated_db_path = "all-results/accumulated_database.json"
        print("📁 [DATABASE TARGET]: Strict automated batch tracking track detected. Targeting standard ledger.")
    
    # FRESH START CONDITION - Erase on Batch 1, maintain history on subsequent loops
    if chunk_offset == 0:
        print(f"🌱 [BATCH 1 POINTER MATCHED (Offset {chunk_offset})]: Reinitializing fresh ledger boundary for {scan_type} track.")
        if os.path.exists(accumulated_db_path):
            try:
                os.remove(accumulated_db_path)
            except Exception as rm_err:
                print(f"⚠️ Warning: Could not clear tracking file: {rm_err}")
    else:
        print(f"🔄 [CHAIN BATCH POINTER MATCHED (Offset {chunk_offset})]: Retaining long-term tracking states across chunks.")

    # Ingest baseline entries from your database branch file ledger into a tracking map
    master_ledger = {}
    if os.path.exists(accumulated_db_path):
        try:
            with open(accumulated_db_path, "r", encoding="utf-8") as r_db:
                historical_records = json.load(r_db)
                if isinstance(historical_records, list):
                    for entry in historical_records:
                        key = (str(entry.get('repo')).strip().lower(), str(entry.get('pr_num')).strip().lower(), str(entry.get('tool')).strip().lower())
                        master_ledger[key] = entry
            print(f"📁 [LEDGER LOG]: Successfully loaded {len(master_ledger)} cumulative scan profiles from branch memory map.")
        except Exception as ledger_ex: 
            print(f"⚠️ History read warning: {ledger_ex}")
            
    seen_pr_keys = set()
    success_markers = []
    if os.path.exists('all-results'):
        success_markers.extend(glob.glob('all-results/*.success'))
        success_markers.extend(glob.glob('all-results/**/*.success', recursive=True))
        success_markers = sorted(list(set(success_markers)))

    print(f"📦 [FOUND ASSETS] Active session markers discovered on disk: {len(success_markers)}")

    # PROCESS FILE ARTIFACTS AND POPULATE SCALAR INDEX VALUES
    for f in success_markers:
        fname = os.path.basename(f)
        parent_dir = os.path.dirname(f)
        parent_name = os.path.basename(parent_dir)

        try:
            name_root = fname.replace('.success', '').replace('.failed', '')
            parts = name_root.split('--')
            
            # Directory naming string fallback mapping tracker for artifact subfolder trees
            if len(parts) < 6 and '--' in parent_name:
                clean_parent = re.sub(r'^sarif-\d+-', '', parent_name)
                parts = clean_parent.split('--')
                
            if len(parts) < 6: 
                continue
            
            # 🎯 EXTRACT 6 DISTINCT ITEMS NATIVELY OFF YOUR FILENAME STRING TOKENS
            raw_repo  = parts[0]
            raw_pr    = parts[1]
            raw_lang  = parts[2]
            raw_agent = parts[3]
            raw_size  = parts[4]
            raw_stars = parts[5] # 👈 GRABS THE SIXTH ELEMENT SAFELY FROM YOUR PATH

            repo_path = raw_repo.replace('_SLASH_', '/')
            pr_num = raw_pr
            lang = raw_lang
            ai_agent_tool = raw_agent.replace('_', ' ')
            live_loc = int(raw_size) if raw_size.isdigit() else 100
            
            # 🎯 SET STARS COUNT DYNAMICALLY FROM THE STRIPPED TOKEN
            repo_stars_count = int(raw_stars) if raw_stars.isdigit() else 0
            
            base_domain = "https://github.com"
            clean_repo_path = repo_path.strip('/')
            full_url = f"{base_domain}/{clean_repo_path}/pull/{pr_num}"
            link_md = f'[#{pr_num}]({full_url})'

            lookup_key = (str(clean_repo_path).strip().lower(), str(pr_num).strip().lower(), str(ai_agent_tool).strip().lower())
            
            h, m, l, total_issues = 0, 0, 0, 0
            committed_files_count = 1
            findings_details = [] 

            custom_json_path = f.replace('.success', '.json')
            nested_json_path = os.path.join(parent_dir, f"{name_root}.json")
            flat_json_path = os.path.join(parent_dir, "summary.json")
            
            target_json_path = ""
            if os.path.exists(custom_json_path): target_json_path = custom_json_path
            elif os.path.exists(nested_json_path): target_json_path = nested_json_path
            elif os.path.exists(flat_json_path): target_json_path = flat_json_path

            if target_json_path and os.path.exists(target_json_path):
                with open(target_json_path, 'r', encoding='utf-8') as sm_f:
                    summary_data = json.load(sm_f)
                    h = int(summary_data.get('high', summary_data.get('H', 0)))
                    m = int(summary_data.get('medium', summary_data.get('M', 0)))
                    l = int(summary_data.get('low', summary_data.get('L', 0)))
                    total_issues = int(summary_data.get('total_issues', summary_data.get('issues', h + m + l)))
                    committed_files_count = int(summary_data.get('files_changed', 1))
                    findings_details = summary_data.get('findings_details', summary_data.get('issues_list', []))
                    
                    cwes_list = summary_data.get('cwes_discovered', summary_data.get('cwes', []))
                    if isinstance(cwes_list, list):
                        clean_cwes = sorted(list(set(str(c).strip().upper() for c in cwes_list if c and str(c).strip())))
                        cwe_display = ', '.join(clean_cwes) if clean_cwes else "None"
                    else:
                        cwe_display = str(cwes_list).strip().upper() if cwes_list else "None"
            else:
                cwe_display = "None"

            cwe_density = round(total_issues / live_loc, 4) if live_loc > 0 else 0.0
            paren_issues_files = f"{total_issues} ({committed_files_count})"
            status_badge = get_live_pr_status(clean_repo_path, pr_num)
            display_loc = 0 if committed_files_count == 0 else live_loc
            
            row_entry = {
                "repo": clean_repo_path, "link": link_md, "tool": ai_agent_tool, "lang": lang,
                "loc": display_loc, "cwes": cwe_display, "h": h, "m": m, "l": l, 
                "issues_files": paren_issues_files, "density": cwe_density, "status": status_badge,
                "has_issues_bool": total_issues > 0, "pr_num": pr_num,
                "findings_details": findings_details,
                "stars": repo_stars_count # 🎯 SAVED SEAMLESSLY FROM YOUR FILENAME TOKENS
            }
            
            # Track today's fresh batch rows for the Markdown Summary
            table_rows.append(row_entry)
            
            # Map the entry straight into your master_ledger map to manage history tracking
            master_ledger[lookup_key] = row_entry
            seen_pr_keys.add(f"{clean_repo_path}#{pr_num}")
            
        except Exception as e: 
            print(f'Error processing success metadata {fname}: {e}')

    # 🎯 STEP C: PURE ATOMIC LIST CONCATENATION FOR THE BRANCH LEDGER
    database_payload = []
    
    # 1. Pull down and preserve the historical records currently sitting on your database branch
    if os.path.exists(accumulated_db_path):
        try:
            with open(accumulated_db_path, "r", encoding="utf-8") as r_db:
                old_records = json.load(r_db)
                if isinstance(old_records, list):
                    for old_item in old_records:
                        old_repo = str(old_item.get('repo', '')).strip().lower()
                        old_pr   = str(old_item.get('pr_num', '')).strip().lower()
                        old_tool = str(old_item.get('tool', '')).strip().lower()
                        
                        # Only keep the old entry if today's run isn't actively overwriting it
                        if (old_repo, old_pr, old_tool) not in master_ledger:
                            database_payload.append(old_item)
        except Exception as r_err:
            print(f"⚠️ Notice: No existing database found to append. Building fresh history track list: {r_err}")

    # 2. Append today's fresh batch rows onto the database tracking payload list array
    for fresh_row in list(master_ledger.values()):
        if fresh_row not in database_payload:
            database_payload.append(fresh_row)

    # Flush the combined database list array out to your database branch tracking folder
    if os.path.dirname(accumulated_db_path):
        os.makedirs(os.path.dirname(accumulated_db_path), exist_ok=True)
        
    with open(accumulated_db_path, "w", encoding="utf-8") as db_w:
        json.dump(database_payload, db_w, indent=2, ensure_ascii=False)
    print(f"💾 [LEDGER FLUSH SUCCESSFUL] Consolidated master data size: {len(database_payload)} entries saved to {accumulated_db_path}.")

    # Restrict summary calculations strictly to today's active batch run
    total_scanned = len(table_rows)
    vulnerable_count = sum(1 for r in table_rows if r.get('has_issues_bool', False))
    total_loc_scanned = sum(int(r.get('loc', 0)) for r in table_rows)
    
    open_count = sum(1 for r in table_rows if "Open" in r.get('status', ''))
    merged_count = sum(1 for r in table_rows if "Merged" in r.get('status', ''))
    closed_count = sum(1 for r in table_rows if "Closed" in r.get('status', ''))

    # Generate Markdown headers
    os.makedirs("report-chunks", exist_ok=True)
    with open("report-chunks/header.md", "w", encoding="utf-8") as out:
        out.write('# 📊 Global Analysis Summary\n\n### Executive Summary\n')
        out.write(f'- **Total PRs Parsed in This Run:** {total_scanned}\n')
        out.write(f'- **Total LOC Scanned in This Run:** {total_loc_scanned} lines\n')
        out.write(f'- **PRs with Issues:** {vulnerable_count} ⚠️ | **Clean PRs:** {total_scanned - vulnerable_count} ✅\n')
        out.write(f'- **Lifecycle Breakdown:** 🟢 Open: {open_count} | 🟣 Merged: {merged_count} | 🔴 Closed: {closed_count}\n\n')

    sorted_rows = sorted(table_rows, key=lambda x: (x.get("repo", ""), x.get("link", "")))
    chunk_size = 50
    row_chunks = [sorted_rows[i:i + chunk_size] for i in range(0, len(sorted_rows), chunk_size)]

    for index, chunk in enumerate(row_chunks):
        chunk_file = f"report-chunks/table_part_{index + 1}.md"
        with open(chunk_file, "w", encoding="utf-8") as out:
            out.write(f"\n### Detailed Scan Logs (Part {index + 1} of {len(row_chunks)})\n")
            
            if is_human_run:
                out.write('| Repository | PR | Status | Lang | PR LOC | CWE Discovered | 🔴 H | 🟡 M | 🔵 L | Total Security Issues (Files) | CWE Density |\n')
                out.write('| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n')
            else:
                out.write('| Repository | PR | Status | AI Tool | Lang | PR LOC | CWE Discovered | 🔴 H | 🟡 M | 🔵 L | Total Security Issues (Files) | CWE Density |\n')
                out.write('| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n')
            
            for r in chunk:
                if is_human_run:
                    out.write(f'| {r.get("repo")} | {r.get("link")} | {r.get("status")} | {r.get("lang")} | {r.get("loc")} | **{r.get("cwes")}** | {r.get("h")} | {r.get("m")} | {r.get("l")} | **{r.get("issues_files")}** | **{r.get("density")}** |\n')
                else:
                    out.write(f'| {r.get("repo")} | {r.get("link")} | {r.get("status")} | {r.get("tool")} | {r.get("lang")} | {r.get("loc")} | **{r.get("cwes")}** | {r.get("h")} | {r.get("m")} | {r.get("l")} | **{r.get("issues_files")}** | **{r.get("density")}** |\n')
                    
    print(f"🧩 Successfully split report into {len(row_chunks) + 1} independent compliance chunks.")

if __name__ == "__main__":
    main()
