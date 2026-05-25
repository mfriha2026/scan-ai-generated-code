import json
import glob
import os

def main():
    matrix_str = os.environ.get('MATRIX_JSON', '{}')
    try:
        matrix_data = json.loads(matrix_str)
        tot = len(matrix_data.get('include', []))
    except Exception:
        tot = 0
        
    all_files = sorted(glob.glob('all-results/**/*.sarif', recursive=True)) if os.path.exists('all-results') else []
    ok_m = len(glob.glob('all-results/**/*.success', recursive=True)) if os.path.exists('all-results') else 0
    ko_m = len(glob.glob('all-results/**/*.failed', recursive=True)) if os.path.exists('all-results') else 0
    
    if tot == 0: 
        tot = ok_m + ko_m
        
    table_rows = []
    total_scanned = 0
    vulnerable_count = 0
    cwe_tracker = {}
    
    # Check if this execution contains human-triage audit markers
    is_human_run = any("Human_Auditor" in os.path.basename(f) for f in all_files)

    for f in all_files:
        fname = os.path.basename(f)
        if fname == 'results.sarif' or '--' not in fname: 
            continue

        try:
            name_root = fname.replace('.sarif', '')
            parts = name_root.split('--')
            if len(parts) < 4: 
                continue
            
            # --- FIX: ADDED REQUIRED LIST STRING ARRAY ARRAY INDICES ---
            repo_path = parts[0].replace('_SLASH_', '/')
            pr_num = parts[1]
            lang = parts[2]
            agent = parts[3].replace('_', ' ')
            
            with open(f) as s: 
                data = json.load(s)
            runs = data.get('runs', [])
            res = []
            
            seen_findings = set()
            for run in runs:
                if isinstance(run, dict):
                    for result in run.get('results', []):
                        rule_id = result.get('ruleId', 'Unknown')
                        
                        locs_data = result.get('locations', [])
                        locs = {}
                        if isinstance(locs_data, list) and len(locs_data) > 0:
                            first_loc = locs_data[0]
                            locs = first_loc.get('physicalLocation', {}) if isinstance(first_loc, dict) else {}
                        elif isinstance(locs_data, dict):
                            locs = locs_data.get('physicalLocation', {})
                        
                        path = locs.get('artifactLocation', {}).get('uri', 'Unknown')
                        line = locs.get('region', {}).get('startLine', '?')
                        
                        fingerprint = f'{rule_id}::{path}::{line}'
                        if fingerprint not in seen_findings:
                            seen_findings.add(fingerprint)
                            res.append(result)
            
            local_cwe_map = {}
            try:
                for run in runs:
                    if not isinstance(run, dict): continue
                    tool = run.get('tool', {})
                    all_rules = []
                    all_rules.extend(tool.get('driver', {}).get('rules', []))
                    for ext in tool.get('extensions', []):
                        all_rules.extend(ext.get('rules', []))
                    
                    for rule in all_rules:
                        r_id = rule.get('id')
                        tags = rule.get('properties', {}).get('tags', [])
                        if r_id not in local_cwe_map:
                            local_cwe_map[r_id] = set()
                        for t in tags:
                            if 'cwe-' in t.lower():
                                c_num = t.lower().split('cwe-')[-1]
                                if len(c_num) < 3:
                                    c_num = c_num.zfill(3)
                                local_cwe_map[r_id].add(f'CWE-{c_num}'.upper())
            except Exception as ex: 
                print(f'Metadata extract warning for {fname}: {ex}')
            
            total_scanned += 1
            if len(res) > 0: 
                vulnerable_count += 1
            
            h, m, l = 0, 0, 0
            CWE_TOP_25 = [
                'CWE-787', 'CWE-079', 'CWE-089', 'CWE-020', 'CWE-125', 'CWE-078', 'CWE-416',
                'CWE-022', 'CWE-352', 'CWE-434', 'CWE-476', 'CWE-502', 'CWE-190', 'CWE-287',
                'CWE-798', 'CWE-862', 'CWE-732', 'CWE-269', 'CWE-306', 'CWE-362', 'CWE-522',
                'CWE-611', 'CWE-918', 'CWE-077', 'CWE-400', 'CWE-088', 'CWE-094'
            ]
            
            for r in res:
                r_id = r.get('ruleId', '')
                level = r.get('level', 'warning')
                cwes_for_rule = local_cwe_map.get(r_id, set())
                is_top_25 = any(c in CWE_TOP_25 for c in cwes_for_rule)
                
                if level == 'error' or is_top_25: h += 1
                elif level == 'warning': m += 1
                else: l += 1
            
            if h > 0: row_severity_badge = '🔴 High'
            elif m > 0: row_severity_badge = '🟡 Medium'
            elif l > 0: row_severity_badge = '🔵 Low'
            else: row_severity_badge = '🟢 Clean'
            
            pr_cwes = set()
            for r in res:
                cwes_for_rule = local_cwe_map.get(r.get('ruleId'), set())
                if cwes_for_rule:
                    for cwe_id in cwes_for_rule:
                        cwe_tracker[cwe_id] = cwe_tracker.get(cwe_id, 0) + 1
                        pr_cwes.add(cwe_id)
            
            cwe_display = ', '.join(sorted(list(pr_cwes))) if pr_cwes else 'None'
            
            unique_files = set()
            for r in res:
                for loc in r.get('locations', []):
                    if isinstance(loc, dict):
                        u_uri = loc.get('physicalLocation', {}).get('artifactLocation', {}).get('uri')
                        if u_uri: unique_files.add(u_uri)
            u_files = len(unique_files)
            
            full_url = '/'.join(['https://github.com', repo_path, 'pull', pr_num])
            link_md = f'[#{pr_num}]({full_url})'
            
            # Conditionally format the data columns depending on the scan type
            if "Human_Auditor" in fname:
                table_rows.append(f'| {repo_path} | {link_md} | {lang} | {row_severity_badge} | **{cwe_display}** | {h} | {m} | {l} | {len(res)} ({u_files}) |')
            else:
                table_rows.append(f'| {repo_path} | {link_md} | {agent} | {lang} | {row_severity_badge} | **{cwe_display}** | {h} | {m} | {l} | {len(res)} ({u_files}) |')
        except Exception as e:
            print(f'Error processing {fname}: {e}')
            
    summary_file = os.environ.get('GITHUB_STEP_SUMMARY', 'summary.md')
    with open(summary_file, 'w') as out:
        out.write('# 📊 Global Analysis Summary\n\n### Executive Summary\n')
        out.write(f'- **Scan Completion Ratio:** {ok_m}/{tot} PR Matrix Scans Completed Successfully 🎉\n')
        if ko_m > 0: 
            out.write(f'- **Isolated Execution Drops:** {ko_m} *(Bypassed cleanly to preserve pipeline status)*\n')
        out.write(f'- **Total PRs Parsed:** {total_scanned}\n')
        out.write(f'- **PRs with Issues:** {vulnerable_count} ⚠️\n')
        out.write(f'- **Clean PRs:** {total_scanned - vulnerable_count} ✅\n\n')
        
        out.write('### Discovered AI Weaknesses (Top 5 CWE Frequency) 🎯\n')
        if cwe_tracker:
            for c, cnt in sorted(cwe_tracker.items(), key=lambda item: item[1], reverse=True)[:5]:
                out.write(f'- **{c}**: Found {cnt} time(s)\n')
        else:
            out.write('- No distinct CWE records mapped.\n')
            
        # Conditionally hide or show the AI Tool column header
        if is_human_run:
            out.write('\n| Repository | PR | Lang | Overall Severity | CWE Discovered | 🔴 H | 🟡 M | 🔵 L | Total (Files) |\n')
            out.write('| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n')
        else:
            out.write('\n| Repository | PR | AI Tool | Lang | Overall Severity | CWE Discovered | 🔴 H | 🟡 M | 🔵 L | Total (Files) |\n')
            out.write('| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n')
            
        for r in sorted(table_rows): 
            out.write(f'{r}\n')

if __name__ == "__main__":
    main()
