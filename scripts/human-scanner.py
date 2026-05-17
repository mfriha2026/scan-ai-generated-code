import subprocess, json, os, time, pandas as pd

def run_command(command, max_retries=2):
    for attempt in range(max_retries):
        try:
            result = subprocess.run(command, capture_output=True, text=True, shell=True, timeout=30)
            if result.returncode == 0: return result
            time.sleep(1)
        except subprocess.TimeoutExpired: continue
    return None

def main():
    # --- CONFIGURATION (TEST LIMIT TO 10) ---
    INPUT_CSV = "human_scan_list.csv" 
    MAX_PR_LINES = 1000 
    SCAN_LIMIT = 10     # Reduced from 500 to 10 for testing
    
    # Exclude list with the problematic/large repositories discovered during scans
    EXCLUDE_REPOS = [
        "BerriAI/litellm", 
        "elastic/kibana",
        "openops-cloud/openops", 
        "DataDog/dd-trace-java", 
        "Azure/azure-sdk-for-js", 
        "Azure/azure-sdk-for-python",
        "microsoft/TypeScript"
    ]
    
    # --- TRACKING ---
    stats = {"added": 0, "too_big": 0, "excluded": 0, "api_error": 0, "duplicates": 0}
    
    if not os.path.exists(INPUT_CSV):
        print('matrix_data={"include":[]}')
        return

    df = pd.read_csv(INPUT_CSV)
    matrix_include = []
    seen_repos = set()

    print(f"--- Starting Human PR Discovery (Target: {SCAN_LIMIT}) ---")
    for _, row in df.iterrows():
        if stats["added"] >= SCAN_LIMIT: break
        
        repo = row['repo_name']
        num = str(row['number'])
        
        if repo in EXCLUDE_REPOS:
            print(f"SKIP: {repo} (Manual Exclude)")
            stats["excluded"] += 1
            continue

        if repo in seen_repos:
            stats["duplicates"] += 1
            continue

        lines_res = run_command(f'gh pr view {num} --repo {repo} --json additions,deletions')
        if lines_res and lines_res.returncode == 0:
            data = json.loads(lines_res.stdout)
            total = data.get("additions", 0) + data.get("deletions", 0)
            if total > MAX_PR_LINES:
                print(f"SKIP: {repo} #{num} (Size: {total} lines)")
                stats["too_big"] += 1
                continue
        else:
            print(f"SKIP: {repo} #{num} (API/Access Error)")
            stats["api_error"] += 1
            continue

        matrix_include.append({
            "pr_num": num, 
            "repo_name": repo, 
            "language": row['primary_language'], 
            "pr_title": row.get('title', 'Untitled'),
            "category_name": f"human--{repo.replace('/', '_SLASH_')}--{num}--{row['primary_language']}"
        })
        
        print(f"ADDED: {repo} #{num} ({total} lines)")
        seen_repos.add(repo)
        stats["added"] += 1
        if stats["added"] % 20 == 0: time.sleep(1)

    print("\n--- Human Discovery Summary ---")
    print(f"✅ Total Added: {stats['added']}")
    print(f"❌ Too Large:  {stats['too_big']}")
    print(f"🚫 Excluded:   {stats['excluded']}")
    print(f"👯 Duplicates: {stats['duplicates']}")
    print(f"⚠️  API Errors: {stats['api_error']}")
    print("-------------------------\n")

    output = json.dumps({"include": matrix_include})
    if 'GITHUB_OUTPUT' in os.environ:
        with open(os.environ['GITHUB_OUTPUT'], 'a') as f: f.write(f'matrix_data={output}\n')
    else: print(f"matrix_data={output}")

if __name__ == '__main__': main()
