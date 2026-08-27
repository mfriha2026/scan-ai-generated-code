import subprocess
import json
import os
import time
import pandas as pd

def run_command(command, max_retries=2):
    for attempt in range(max_retries):
        try:
            result = subprocess.run(command, capture_output=True, text=True, shell=True, timeout=30)
            if result.returncode == 0: 
                return result
            time.sleep(1)
        except subprocess.TimeoutExpired: 
            continue
    return None

def main():
    # --- CONFIGURATION ---
    INPUT_CSV = "aidev_scan_list.csv"
    MAX_PR_LINES = 1000 
    SCAN_LIMIT = 250     # Pure maximum slots per batch pass
    
    # 🚀 CHUNK OFFSET AND EXTRACTION COUNTER INGESTION
    try:
        chunk_offset = int(os.environ.get('CHUNK_OFFSET', '0'))
    except ValueError:
        chunk_offset = 0
        
    try:
        past_extracted = int(os.environ.get('CURRENT_EXTRACTED', '0'))
    except ValueError:
        past_extracted = 0
    
    # --- TRACKING ---
    stats = {"added": 0, "too_big": 0, "excluded": 0, "api_error": 0, "duplicates": 0, "empty": 0}
    EXCLUDE_REPOS = [
        "BerriAI/litellm", "elastic/kibana", "tinygrad/tinygrad", "classmethod/tsumiki", 
        "camunda/camunda", "Azure/azure-sdk-for-python", "wzdavid/ThinkRAG", "Azure/azure-sdk-for-js", 
        "typehero/typehero", "ruvnet/claude-flow", "microsoft/TypeScript", "Azure/azure-sdk-for-java", "nuxeo/nuxeo",
        "cuckoo-network/cuckoo", "goniszewski/grimoire"
    ]
    
    if not os.path.exists(INPUT_CSV):
        print('matrix_data={"include":[]}')
        return

    df = pd.read_csv(INPUT_CSV)
    matrix_include = []
    
    seen_repos = set()
    accumulated_db_path = "all-results/accumulated_database.json"

    # 🎯 STEP 1: Copy the repos from the database file to seen_repos at start
    if chunk_offset > 0 and os.path.exists(accumulated_db_path):
        try:
            with open(accumulated_db_path, "r", encoding="utf-8") as db_f:
                historical_rows = json.load(db_f)
                if isinstance(historical_rows, list):
                    for r in historical_rows:
                        # Extract the exact repository text name field matching your layout keys
                        hist_repo = r.get('repo_name', r.get('repo', '')).strip()
                        if hist_repo:
                            seen_repos.add(hist_repo)
                    print(f"📥 Loaded {len(seen_repos)} unique repositories from master database memory.")
        except Exception as cache_err:
            print(f"⚠️ Warning: Could not hydrate cross-batch deduplication memory: {cache_err}")
    else:
        print("🧼 [CLEAN INITIAL PASS] Starting clean discovery session without old historical cache injections.")

    processed_count = 0

    print(f"--- Starting Discovery (Offset: {chunk_offset} | Target Limit: {SCAN_LIMIT} PRs) ---")
    for _, row in df.iterrows():
        # 🚀 THE CRITICAL STOP FIX: If we successfully reached 5 items, stop loop execution IMMEDIATELY!
        if stats["added"] >= SCAN_LIMIT: 
            break
        
        # CHUNK GUARD SLICER: Skips rows belonging to previous batch execution runs
        if processed_count < chunk_offset:
            processed_count += 1
            continue
            
        processed_count += 1
        
        repo = row['repo_name']
        num = str(row['number'])
        title = str(row['title'])
        lang = str(row['primary_language'])
        agent = str(row['agent_name'])
        repo_stars = str(row.get('repo_stars', '0'))
        
        if repo in EXCLUDE_REPOS:
            print(f"SKIP: {repo} (Manual Exclude)")
            stats["excluded"] += 1
            continue

        # 🎯 THE DEDUPLICATION FILTER: If PR repo is already in seen_repos, skip it!
        if repo in seen_repos:
            print(f"SKIP: {repo} #{num} (Duplicate Repo Filtered Natively across historical batches)")
            stats["duplicates"] += 1
            continue

        lines_res = run_command(f'gh pr view {num} --repo {repo} --json additions,deletions')
        if lines_res: 
            data_res = json.loads(lines_res.stdout)
            total = data_res.get("additions", 0) + data_res.get("deletions", 0)
            
            # ZERO-CHANGE EXCLUSION GUARD: Drops any PR that has 0 modifications
            if total == 0:
                print(f"SKIP: {repo} #{num} (Empty PR: 0 files/lines change)")
                stats["empty"] += 1
                continue
                
            if total > MAX_PR_LINES:
                print(f"SKIP: {repo} #{num} (Size: {total} lines)")
                stats["too_big"] += 1
                continue
        else:
            print(f"SKIP: {repo} #{num} (API/Access Error)")
            stats["api_error"] += 1
            continue

        # 🎯 MARK AS SEEN: Add the repo to our set only upon a completely successful scan extraction
        seen_repos.add(repo)

        matrix_include.append({
            "pr_num": num, 
            "repo_name": repo, 
            "language": lang, 
            "pr_title": title, 
            "agent_name": agent,
            "repo_stars": repo_stars,
            "category_name": f"{repo.replace('/', '_SLASH_')}--{num}--{lang}--{agent.replace(' ', '_')}"
        })
        
        print(f"ADDED: {repo} #{num} ({total} lines)")
        stats["added"] += 1

    # 🚀 ACCURATE POINTER BOUNDARY ARITHMETIC (For sliding window calculation)
    next_offset = chunk_offset + len(matrix_include) + stats["too_big"] + stats["empty"] + stats["excluded"] + stats["duplicates"] + stats["api_error"]
    
    # Calculate the true accumulated total count of PRs added to scan matrix across runs
    total_extracted = past_extracted + stats["added"]

    # Check if there are physical rows remaining in your CSV data list
    has_more_data = "true" if next_offset < len(df) and stats["added"] > 0 else "false"

    # TARGET TRACKING GRADUATION: Stops looping ONLY when you hit your exact extraction target milestone goal of 10 PRs!
    if total_extracted >= 1000:
        print(f"🧪 [TEST CHAIN] Target total goal of 1000 PR extractions reached. Terminating chaining loop sequence gracefully.")
        has_more_data = "false"
    elif has_more_data == "true":
        print(f"🧪 [TEST CHAIN] Pass complete. Chaining next batch of 250. CSV Cursor Pointer: {next_offset} | Extracted total: {total_extracted}")

    output = json.dumps({"include": matrix_include})
    
    # EXPORT SIGNAL METRICS DIRECTLY TO JOB CONTEXT BOUNDARIES
    if 'GITHUB_OUTPUT' in os.environ:
        with open(os.environ['GITHUB_OUTPUT'], 'a') as f: 
            f.write(f'matrix_data={output}\n')
            f.write(f'next_offset={next_offset}\n')
            f.write(f'has_more_data={has_more_data}\n')
            f.write(f'total_extracted={total_extracted}\n')

    print("\n--- Discovery Summary ---")
    print(f"✅ Total Added to Matrix: {stats['added']}")
    print(f"❌ Skipped (Too Large):   {stats['too_big']}")
    print(f"💨 Skipped (Empty 0 LOC):  {stats['empty']}")
    print(f"🚫 Skipped (Excluded):    {stats['excluded']}")
    print(f"👯 Skipped (Duplicates):  {stats['duplicates']}")
    print(f"⚠️  Skipped (API Errors): {stats['api_error']}")
    print(f"🔢 Next Pointer Offset:   {next_offset}")
    print(f"🔄 Continues Remaining:   {has_more_data}")
    print("-------------------------\n")

if __name__ == '__main__': 
    main()
