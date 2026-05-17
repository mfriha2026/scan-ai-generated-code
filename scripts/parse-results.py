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
    run = runs[0]
        
    # --- FIXED BULLETPROOF CWE EXTRACTOR ---
    cwe_map = {}
    try:
        # Collect all possible rule locations (Driver rules + Extension rules)
        all_rules = []
        tool = run.get('tool', {})
        
        # 1. Main Driver Rules
        all_rules.extend(tool.get('driver', {}).get('rules', []))
        
        # 2. Extension Pack Rules (Where matrix metadata usually moves them)
        for ext in tool.get('extensions', []):
            all_rules.extend(ext.get('rules', []))

        # Map each ruleId to its respective CWE text strings
        for rule in all_rules:
            rule_id = rule.get('id')
            if not rule_id: continue
            
            tags = rule.get('properties', {}).get('tags', [])
            cwes = []
            for tag in tags:
                if 'cwe-' in tag.lower():
                    # Parse tag variations e.g., 'external/cwe/cwe-79'
                    cwe_num = tag.lower().split('cwe-')[-1]
                    cwes.append(f"CWE-{cwe_num}")
            if cwes:
                cwe_map[rule_id] = ", ".join(sorted(list(set(cwes)))).upper()
    except Exception as e:
        print(f"Metadata mapping warning: {e}")

    results = run.get('results', [])
    summary_md = f"\n### 🛡️ Analysis Details: {len(results)} Issues Found\n"
    
    if results:
        summary_md += "| Severity | CWE | Vulnerability | File:Line | Description |\n| :--- | :--- | :--- | :--- | :--- |\n"
        icons = {"error": "🔴 High", "warning": "🟡 Medium", "note": "🔵 Low"}
        for res in results:
            locs = res.get('locations', [{}])[0].get('physicalLocation', {})
            path = locs.get('artifactLocation', {}).get('uri', 'Unknown')
            line = locs.get('region', {}).get('startLine', '?')
            level = res.get('level', 'warning')
            rule_id = res.get('ruleId', 'Unknown')
            
            cwe_display = cwe_map.get(rule_id, "N/A")
            msg = res.get('message', {}).get('text', 'No description').split('\n')[0]
            summary_md += f"| {icons.get(level, '🟡')} | **{cwe_display}** | `{rule_id}` | `{path}:{line}` | {msg} |\n"

    summary_file = os.environ.get('GITHUB_STEP_SUMMARY', 'summary.md')
    with open(summary_file, 'a') as f:
        f.write(summary_md)

if __name__ == "__main__":
    main()
