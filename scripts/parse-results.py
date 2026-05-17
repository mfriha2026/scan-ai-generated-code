import json, os, sys

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
            locs = res.get('locations', [{}]).get('physicalLocation', {})
            path = locs.get('artifactLocation', {}).get('uri', 'Unknown')
            line = locs.get('region', {}).get('startLine', '?')
            
            fingerprint = f"{rule_id}::{path}::{line}"
            if fingerprint not in seen_findings:
                seen_findings.add(fingerprint)
                consolidated_results.append(res)

    summary_md = f"\n### 🛡️ Analysis Details: {len(consolidated_results)} Distinct Issues Found\n"
    
    if consolidated_results:
        summary_md += "| Severity | CWE | Vulnerability | File:Line | Description |\n| :--- | :--- | :--- | :--- | :--- |\n"
        
        # DEFINED CRITICAL CWES FOR LOCAL ESCALATION
        CRITICAL_CWES = ['CWE-078', 'CWE-088', 'CWE-094', 'CWE-502']
        
        for res in consolidated_results:
            locs = res.get('locations', [{}]).get('physicalLocation', {})
            path = locs.get('artifactLocation', {}).get('uri', 'Unknown')
            line = locs.get('region', {}).get('startLine', '?')
            level = res.get('level', 'warning')
            rule_id = res.get('ruleId', 'Unknown')
            
            cwes_set = cwe_map.get(rule_id, set())
            cwe_display = ", ".join(sorted(list(cwes_set))) if cwes_set else "N/A"
            
            # FIXED SMART SEVERITY MAPPING: Escalate severe CWEs to High icon status
            is_critical_cwe = any(c in CRITICAL_CWES for c in cwes_set)
            if level == 'error' or is_critical_cwe:
                icon_display = "🔴 High"
            elif level == 'warning':
                icon_display = "🟡 Medium"
            else:
                icon_display = "🔵 Low"
            
            msg = res.get('message', {}).get('text', 'No description').split('\n')[0]
            summary_md += f"| {icon_display} | **{cwe_display}** | `{rule_id}` | `{path}:{line}` | {msg} |\n"

    summary_file = os.environ.get('GITHUB_STEP_SUMMARY', 'summary.md')
    with open(summary_file, 'a') as f:
        f.write(summary_md)

if __name__ == "__main__":
    main()
