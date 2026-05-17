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
        
    # --- EXTRACT CWE METADATA FROM SARIF RULES ---
    # CodeQL stores CWE tags inside the tool rule extensions [1, 2]
    cwe_map = {}
    try:
        rules = runs[0].get('tool', {}).get('driver', {}).get('rules', [])
        for rule in rules:
            rule_id = rule.get('id')
            tags = rule.get('properties', {}).get('tags', [])
            cwes = []
            for tag in tags:
                # CodeQL uses tags like 'external/cwe/cwe-79' or 'security/cwe/cwe-89' [1, 2]
                if 'cwe-' in tag.lower():
                    parts = tag.lower().split('cwe-')
                    if len(parts) > 1:
                        cwes.append(f"CWE-{parts[1]}")
            if cwes:
                cwe_map[rule_id] = ", ".join(sorted(list(set(cwes)))).upper()
    except Exception:
        pass # Fallback safely if structure differs

    results = runs[0].get('results', [])
    summary_md = f"\n### 🛡️ Analysis Details: {len(results)} Issues Found\n"
    
    if results:
        # Added 'CWE' column to table header
        summary_md += "| Severity | CWE | Vulnerability | File:Line | Description |\n| :--- | :--- | :--- | :--- | :--- |\n"
        icons = {"error": "🔴 High", "warning": "🟡 Medium", "note": "🔵 Low"}
        for res in results:
            locs = res.get('locations', [{}])[0].get('physicalLocation', {})
            path = locs.get('artifactLocation', {}).get('uri', 'Unknown')
            line = locs.get('region', {}).get('startLine', '?')
            level = res.get('level', 'warning')
            rule_id = res.get('ruleId', 'Unknown')
            
            # Lookup CWE tag for this specific rule ID
            cwe_display = cwe_map.get(rule_id, "N/A")
            
            msg = res.get('message', {}).get('text', 'No description').split('\n')[0]
            # Formatted table string with the new CWE field
            summary_md += f"| {icons.get(level, '🟡')} | **{cwe_display}** | `{rule_id}` | `{path}:{line}` | {msg} |\n"

    summary_file = os.environ.get('GITHUB_STEP_SUMMARY', 'summary.md')
    with open(summary_file, 'a') as f:
        f.write(summary_md)

if __name__ == "__main__":
    main()
