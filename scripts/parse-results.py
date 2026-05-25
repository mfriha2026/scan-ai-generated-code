import json
import os
import sys

def main():
    sarif_path = "results.sarif"
    if not os.path.exists(sarif_path):
        return
        
    try:
        with open(sarif_path, 'r') as f:
            data = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return

    runs = data.get('runs', [])
    if not runs:
        return
        
    # --- BULLETPROOF CWE EXTRACTOR ---
    cwe_map = {}
    try:
        all_rules = []
        for run in runs:
            if not isinstance(run, dict): continue
            tool = run.get('tool', {})
            all_rules.extend(tool.get('driver', {}).get('rules', []))
            for ext in tool.get('extensions', []):
                all_rules.extend(ext.get('rules', []))

        for rule in all_rules:
            rule_id = rule.get('id')
            if not rule_id: continue
            
            tags = rule.get('properties', {}).get('tags', [])
            if rule_id not in cwe_map:
                cwe_map[rule_id] = set()
            for tag in tags:
                if 'cwe-' in tag.lower():
                    cwe_num = tag.lower().split('cwe-')[-1]
                    if len(cwe_num) < 3:
                        cwe_num = cwe_num.zfill(3)
                    cwe_map[rule_id].add(f"CWE-{cwe_num}".upper())
    except Exception as e:
        print(f"Metadata mapping warning: {e}")

    # --- AGGREGATE RESULTS & DEDUPLICATE LINES ---
    consolidated_results = []
    seen_findings = set()

    for run in runs:
        if not isinstance(run, dict): continue
        for res in run.get('results', []):
            rule_id = res.get('ruleId', 'Unknown')
            locs_arr = res.get('locations', [])
            
            # --- FIX: TRACK DEDUPLICATION ACROSS ALL SUB-LOCATIONS ---
            is_new_finding = False
            primary_path = "Unknown"
            primary_line = "?"
            
            if isinstance(locs_arr, list) and len(locs_arr) > 0:
                for loc_entry in locs_arr:
                    if not isinstance(loc_entry, dict): continue
                    locs = loc_entry.get('physicalLocation', {})
                    path = locs.get('artifactLocation', {}).get('uri', 'Unknown')
                    line = locs.get('region', {}).get('startLine', '?')
                    
                    if primary_path == "Unknown":
                        primary_path = path
                        primary_line = line
                    
                    fingerprint = f"{rule_id}::{path}::{line}"
                    if fingerprint not in seen_findings:
                        seen_findings.add(fingerprint)
                        is_new_finding = True
            elif isinstance(locs_arr, dict):
                locs = locs_arr.get('physicalLocation', {})
                primary_path = locs.get('artifactLocation', {}).get('uri', 'Unknown')
                primary_line = locs.get('region', {}).get('startLine', '?')
                
                fingerprint = f"{rule_id}::{primary_path}::{primary_line}"
                if fingerprint not in seen_findings:
                    seen_findings.add(fingerprint)
                    is_new_finding = True

            if is_new_finding:
                # Store the primary location references explicitly for row mapping
                res['_primary_path'] = primary_path
                res['_primary_line'] = primary_line
                consolidated_results.append(res)

    summary_md = f"\n### 🛡️ Analysis Details: {len(consolidated_results)} Distinct Issues Found\n"
    
    if consolidated_results:
        summary_md += "| Severity | CWE | Vulnerability | File:Line | Description |\n| :--- | :--- | :--- | :--- | :--- |\n"
        
        CWE_TOP_25 = [
            'CWE-787', 'CWE-079', 'CWE-089', 'CWE-020', 'CWE-125', 'CWE-078', 'CWE-416',
            'CWE-022', 'CWE-352', 'CWE-434', 'CWE-476', 'CWE-502', 'CWE-190', 'CWE-287',
            'CWE-798', 'CWE-862', 'CWE-732', 'CWE-269', 'CWE-306', 'CWE-362', 'CWE-522',
            'CWE-611', 'CWE-918', 'CWE-077', 'CWE-400', 'CWE-088', 'CWE-094'
        ]
        
        for res in consolidated_results:
            path = res.get('_primary_path', 'Unknown')
            line = res.get('_primary_line', '?')
            level = res.get('level', 'warning')
            rule_id = res.get('ruleId', 'Unknown')
            
            cwes_set = cwe_map.get(rule_id, set())
            cwe_display = ", ".join(sorted(list(cwes_set))) if cwes_set else "N/A"
            
            is_top_25 = any(c in CWE_TOP_25 for c in cwes_set)
            
            if level == 'error' or is_top_25:
                icon_display = "🔴 High"
            elif level == 'warning':
                icon_display = "🟡 Medium"
            else:
                icon_display = "🔵 Low"
            
            msg = res.get('message', {}).get('text', 'No description').split('\n')[0]
            summary_md += f"| {icon_display} | **{cdisplay if 'cwe_display' in locals() else cwe_display}** | `{rule_id}` | `{path}:{line}` | {msg} |\n"

    summary_file = os.environ.get('GITHUB_STEP_SUMMARY', 'summary.md')
    with open(summary_file, 'a') as f:
        f.write(summary_md)

if __name__ == "__main__":
    main()
