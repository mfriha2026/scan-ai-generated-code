# 📊 AI & Human Scanner Workspace Baseline Anchor

> **System Note for AI Assistants:** This repository utilizes a split-file parallel matrix architecture. The core parsing loops are decoupled from inline workflow code to maximize reliability and prevent formatting or truncation errors.

## 🛠️ Repository File Tree Map
1. **`.github/workflows/codeql-scan.yml`**: Automated pipeline fanning out to scan up to 20 AI pull requests concurrently in a parallel matrix loop. Drops out files to artifacts pool and runs reporting.
2. **`.github/workflows/human-codeql-scan.yml`**: Manual companion auditing pipeline fanning out to scan up to 20 user-specified manual pull requests concurrently. Mirrors the identical parallel step configurations.
3. **`scripts/ai-scanner.py`**: Reads `aidev_scan_list.csv` dynamically, sets line threshold skips (<1000 lines), and sets target limit counts (`SCAN_LIMIT = 20`) to feed the parent automated matrix.
4. **`scripts/human-scanner.py`**: Reads `human_scan_list.csv` dynamically, tracks large repos, and appends a balanced fallback `agent_name: "Human_Auditor"` token to prevent empty string split crashes.
5. **`scripts/parse-results.py`**: Localized step details engine writing append metrics detail data straight to individual runners via `$GITHUB_STEP_SUMMARY`.
6. **`scripts/consolidate-report.py`**: Global data aggregation script. Consolidates multi-runner success/failed tracking tags, reads rule vectors, and outputs the comprehensive executive summaries.

## ⚠️ Matrix Reporting & Layout Rules
* **Parallel Status Constraints**: Step-level protections (`continue-on-error: true` inside worker tasks) are used to absorb local environment drops or timeouts gracefully, ensuring the core platform pipeline stays Green.
* **Conditional UI Column Hiding**: `consolidate-report.py` utilizes smart filename prefix detection (`fname.startswith('human--')`). 
  * If a human run is processed, it automatically filters out the **"AI Tool"** markdown table header column and its matching dataset row cells entirely.
  * If an automated scanner run is processed, the **"AI Tool"** and **"Overall Severity"** columns are fully displayed in their native configuration tracks.
