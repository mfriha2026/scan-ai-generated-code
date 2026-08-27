import pandas as pd
import sys

def extract_human_data():
    print("Streaming Human AIDev tables from Hugging Face...")
    try:
        pr_df = pd.read_parquet("hf://datasets/hao-li/AIDev/human_pull_request.parquet")
        repo_df = pd.read_parquet("hf://datasets/hao-li/AIDev/repository.parquet")

        left_key = 'repo_url'
        right_key = 'url' 

        if left_key not in pr_df.columns or right_key not in repo_df.columns:
            print(f"Column mismatch!")
            sys.exit(1)

        print("Joining tables on PR.repo_url and Repo.url...")
        merged_df = pd.merge(
            pr_df, 
            repo_df, 
            left_on=left_key, 
            right_on=right_key, 
            how='inner', 
            suffixes=('_pr', '_repo')
        )

        if merged_df.empty:
            print("Error: Merge resulted in empty dataset.")
            sys.exit(1)

        supported_langs = ['Python', 'JavaScript', 'TypeScript', 'Java', 'Ruby']
        filtered_df = merged_df[
            (merged_df['stars'] > 500) &
            (merged_df['language'].isin(supported_langs))
        ].copy()

        # Normalize language
        filtered_df['language'] = filtered_df['language'].str.lower()
        filtered_df.loc[filtered_df['language'] == 'typescript', 'language'] = 'javascript'

        # Sort and Limit
        filtered_df['created_at'] = pd.to_datetime(filtered_df['created_at'])
        filtered_df = filtered_df.sort_values(by='created_at', ascending=False)
        
        # 🚀 LOC COLUMN REMOVED: Exporting only verified, meaningful properties
        scan_list = filtered_df.head(10000)[['full_name', 'number', 'title', 'language', 'stars']].rename(columns={
            'full_name': 'repo_name',
            'language': 'primary_language',
            'stars': 'repo_stars'
        })
        
        scan_list['agent_name'] = 'human'
        scan_list.to_csv("human_scan_list.csv", index=False)
        print(f"Success: Created human_scan_list.csv with {len(scan_list)} entries.")

    except Exception as e:
        print(f"FAILED: {e}")
        sys.exit(1)

if __name__ == "__main__":
    extract_human_data()
