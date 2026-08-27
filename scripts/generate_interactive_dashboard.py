import os
import json
import re

def main():
    output_path = "docs/GLOBAL_INTERACTIVE_REPORT.html"
    
    # Check the environment variable to automatically point to the correct file path
    scan_type = os.environ.get("SCAN_TYPE", "automated").lower().strip()
    
    if scan_type == "human":
        json_path = "all-results/human_accumulated_database.json"
        report_title = "👨‍💻 Human Pull Requests - Consolidated Summary Report"
        print("📊 [ENGINE LOG]: Running in HUMAN audit mode. Target path set to human ledger.")
    else:
        json_path = "all-results/accumulated_database.json"
        report_title = "🤖 AI-Generated Pull Requests - Consolidated Summary Report"
        print("📊 [ENGINE LOG]: Running in AI automated mode. Target path set to standard ledger.")
        
    os.makedirs("all-results", exist_ok=True)
    os.makedirs("docs", exist_ok=True)

    # Ingest baseline entries from the database branch file ledger
    records_list = []
    if os.path.exists(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                records_list = json.load(f)
            print(f"📁 [ENGINE LOG]: Loaded {len(records_list)} database entries.")
        except Exception as err:
            print(f"❌ Error loading database: {err}")

    # Calculate global statistical distributions for the summary card layout
    total_scanned = len(records_list)
    vulnerable_count = sum(1 for r in records_list if r.get('has_issues_bool', False))
    total_loc_scanned = sum(int(r.get('loc', 0)) for r in records_list)
    
    open_count = sum(1 for r in records_list if "Open" in str(r.get('status', '')))
    merged_count = sum(1 for r in records_list if "Merged" in str(r.get('status', '')))
    closed_count = sum(1 for r in records_list if "Closed" in str(r.get('status', '')))

    header_html = f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><title>{report_title}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto; background-color: #f6f8fa; padding: 40px; color: #24292f; }}
        h1 {{ border-bottom: 1px solid #d0d7de; padding-bottom: 10px; }}
        .card {{ background: #fff; border: 1px solid #d0d7de; border-radius: 6px; padding: 20px; margin-bottom: 30px; }}
        table {{ width: 100%; border-collapse: collapse; font-size: 14px; background: #fff; border: 1px solid #d0d7de; border-radius: 6px; }}
        th {{ background: #f6f8fa; padding: 12px; font-weight: 600; border-bottom: 2px solid #d0d7de; text-align: left; }}
        td {{ padding: 12px; border-bottom: 1px solid #d0d7de; }}
        .vulnerable-row {{ background-color: #ffebe9 !important; }}
        .badge {{ display: inline-block; padding: 2px 8px; font-size: 12px; font-weight: 500; border-radius: 2em; }}
        .badge-vuln {{ background-color: #cf222e; color: #fff; }}
        .badge-clean {{ background-color: #2da44e; color: #fff; }}
        .details-row {{ display: none; background: #fafafa; }}
        .details-container {{ padding: 15px 30px; background: #fff8f8; border-left: 4px solid #cf222e; }}
        .details-table {{ width: 100%; border-collapse: collapse; font-size: 13px; margin-top: 10px; }}
        .details-table th {{ background: #eaecef; }}
        .toggle-btn {{ cursor: pointer; color: #0969da; font-weight: bold; background: none; border: none; }}
    </style>
    <script>
        function toggleDetails(rowId, btn) {{
            var el = document.getElementById(rowId);
            if (el.style.display === "table-row") {{ el.style.display = "none"; btn.innerHTML = "▶ View Details"; }}
            else {{ el.style.display = "table-row"; btn.innerHTML = "▼ View Details"; }}
        }}

        let cweSortToggleState = false;

        function sortCweColumn(headerElement) {{
            const tableBody = document.getElementById('tableBodyContainer');
            if (!tableBody) return;
            
            const indicator = headerElement.querySelector('.sort-indicator');
            cweSortToggleState = !cweSortToggleState;

            if (indicator) {{
                if (cweSortToggleState) {{
                    indicator.innerText = '▲';
                    indicator.style.color = '#38bdf8';
                }} else {{
                    indicator.innerText = '▼';
                    indicator.style.color = '#fbbf24';
                }}
            }}

            const mainRows = [];
            const allRows = tableBody.children;
            for (let i = 0; i < allRows.length; i++) {{
                const r = allRows[i];
                if (r.tagName === 'TR' && !r.id && r.parentNode === tableBody) {{
                    mainRows.push(r);
                }}
            }}

            mainRows.sort((rowA, rowB) => {{
                // 🎯 SORT MATCH: Explicitly mapped to cell index column 8
                const cellA = (rowA.cells && rowA.cells[8]) ? rowA.cells[8].innerText.trim() : 'None';
                const cellB = (rowB.cells && rowB.cells[8]) ? rowB.cells[8].innerText.trim() : 'None';

                const hasCweA = (cellA.includes('CWE-') || (cellA !== 'None' && cellA !== ''));
                const hasCweB = (cellB.includes('CWE-') || (cellB !== 'None' && cellB !== ''));

                if (cweSortToggleState) {{
                    if (hasCweA && !hasCweB) return -1;
                    if (!hasCweA && hasCweB) return 1;
                    return cellA.localeCompare(cellB);
                }} else {{
                    if (!hasCweA && hasCweB) return -1;
                    if (hasCweA && !hasCweB) return 1;
                    return cellB.localeCompare(cellA);
                }}
            }});

            mainRows.forEach((mainRow) => {{
                tableBody.appendChild(mainRow);
                const detailsId = mainRow.getAttribute('data-details-id');
                if (detailsId) {{
                    const detailRowEl = document.getElementById(detailsId);
                    if (detailRowEl) {{
                        tableBody.appendChild(detailRowEl);
                    }}
                }}
            }});
        }}
    </script></head><body>
    <h1>📊 {report_title}</h1>
    <div class="card">
        <h3>📈 Executive Summary</h3>
        <ul>
            <li><strong>Total PRs Scanned:</strong> {total_scanned}</li>
            <li><strong>Total LOC Scanned:</strong> {total_loc_scanned} lines</li>
            <li><strong>PRs with Issues:</strong> <span class="badge badge-vuln">{vulnerable_count} Vulnerable</span> | <span class="badge badge-clean">{total_scanned - vulnerable_count} Clean</span></li>
            <li><strong>Lifecycle Status Breakdown:</strong> 🟢 Open: {open_count} | 🟣 Merged: {merged_count} | 🔴 Closed: {closed_count}</li>
        </ul>
    </div>
    <h3>🔍 Detailed Scan Records Ledger</h3>
    <table style="width: 100%; border-collapse: collapse; background: transparent; table-layout: fixed;">
        <thead>
            <tr style="font-size: 13px; font-weight: 600; background: transparent;">
                <th style="width: 11%; padding: 12px; text-align: left; background: transparent;">Security Alert Status</th>
                <th style="width: 15%; padding: 12px; text-align: left; background: transparent;">Repository Target</th>
                
                <!-- 🎯 HEADER COMPLIANCE COLUMN #3: Injected Repository Stars directly next to target repo -->
                <th style="width: 8%; padding: 12px; text-align: left; background: transparent;">Repository Stars</th>
                
                <th style="width: 9%; padding: 12px; text-align: left; background: transparent; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">PR Reference Link</th>
                <th style="width: 8%; padding: 12px; text-align: left; background: transparent;">Status</th>
                <th style="width: 11%; padding: 12px; text-align: left; background: transparent;">AI Tool Engine</th>
                <th style="width: 9%; padding: 12px; text-align: left; background: transparent;">Language</th>
                <th style="width: 5%; padding: 12px; text-align: left; background: transparent;">LOC</th>
                <th onclick="sortCweColumn(this)" style="width: 12%; padding: 12px; text-align: left; cursor: pointer; user-select: none; white-space: nowrap; background: transparent;">
                    CWE Discovered <span class="sort-indicator" style="margin-left: 4px; font-weight: bold; color: #64748b; font-size: 10px; letter-spacing: -1px;">▲▼</span>
                </th>
                <th style="width: 3%; padding: 12px; text-align: center; background: transparent;">🔴</th>
                <th style="width: 3%; padding: 12px; text-align: center; background: transparent;">🟡</th>
                <th style="width: 3%; padding: 12px; text-align: center; background: transparent;">🔵</th>
                <th style="width: 9%; padding: 12px; text-align: left; background: transparent;">Total Issues (Files)</th>
            </tr>
        </thead>
        <tbody id="tableBodyContainer">
    """

    body_html = ""
    row_index_counter = 0
    for r in records_list:
        row_index_counter += 1
        row_id = f"drawer_row_idx_{row_index_counter}"
        
        repo = str(r.get('repo', 'Unknown'))
        
        # 🎯 THE PRODUCTION FIX: Clean up any trailing bracket wrappers so the link resolves to a true web URL
        raw_db_url = str(r.get('link', '#')).strip()
        pr_display_num = str(r.get('pr_num', 'Link'))
        
        # If the database string contains Markdown characters, strip them down to the clean web address
        if '](' in raw_db_url:
            raw_db_url = raw_db_url.split('](')[-1].rstrip(')')
            
        anchor_tag = f'<a href="{raw_db_url}" target="_blank" style="text-decoration: none; color: #0969da; font-weight: 500; white-space: nowrap;">#{pr_display_num} ↗</a>'
        
        tool = str(r.get('tool', 'CodeQL'))
        lang = str(r.get('lang', 'Unknown'))
        loc = str(r.get('loc', '0'))
        cwes_found = str(r.get('cwes', 'None'))
        status = str(r.get('status', '🟣 Merged'))
        issues_files = str(r.get('issues_files', '0 (0)'))
        
        has_flaw = r.get('has_issues_bool', False)
        findings_list = r.get('findings_details', [])
        repo_stars_value = r.get('stars', 0)

        if has_flaw:
            row_class = ' class="vulnerable-row"'
            alert_prefix = f'<button class="toggle-btn" onclick="toggleDetails(\'{row_id}\', this)">▶ View Details</button>'
        else:
            row_class = ''
            alert_prefix = '<span class="badge badge-clean">✅ Clean Pass</span>'

        sub_table_rows = ""
        if has_flaw and findings_list:
            for bug in findings_list:
                vuln_title = bug.get('vulnerability', 'Unknown Rule')

                raw_text = str(bug.get('description', '')).strip()

                # Step 1: Strip the CodeQL brackets and numbers [text](num) -> text
                clean_text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', raw_text)

                # Step 2: Split into sentences, deduplicate them while preserving order, and rebuild
                sentences = re.split(r'(?<=[.!?])\s+', clean_text.strip())
                unique_sentences = list(dict.fromkeys(sentences))
                final_text = " ".join(unique_sentences)

                # 🎯 BROWSER RENDERING FIX: Escape HTML angle brackets so the browser prints '<script' as raw text instead of a code tag!
                desc_body = final_text.replace('<', '&lt;').replace('>', '&gt;')
                
                file_line_info = bug.get('file_line', 'File')
                severity_val = bug.get('severity_label', '🟡 Medium')
                
                resolved_cwes = bug.get('cwes', [])
                cwe_label_suffix = f" ({', '.join(sorted(list(resolved_cwes)))})" if resolved_cwes else " (CWE: N/A)"
                display_rule_text = f"{vuln_title}{cwe_label_suffix}"

                sub_table_rows += f"""
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #d0d7de;"><span class="badge" style="background-color: #cf222e; color:white;">{severity_val}</span></td>
                    <td style="padding: 8px; border-bottom: 1px solid #d0d7de;"><strong>{display_rule_text}</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #d0d7de;"><code>{file_line_info}</code></td>
                    <td style="padding: 8px; border-bottom: 1px solid #d0d7de;">{desc_body}</td>
                </tr>"""

        body_html += f"""
        <tr{row_class} data-details-id="{row_id}">
            <td style="padding: 12px; vertical-align: middle;">{alert_prefix}</td>
            <td style="padding: 12px; vertical-align: middle; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;"><strong>{repo}</strong></td>
            
            <!-- 🎯 CELL DATA COLUMN #3: Repository Stars injected dynamically next to Target Repo -->
            <td style="padding: 12px; vertical-align: middle; font-weight: 500; color: #57606a;">⭐ {repo_stars_value:,}</td>
            
            <td style="padding: 12px; vertical-align: middle;">{anchor_tag}</td>
            <td style="padding: 12px; vertical-align: middle;">{status}</td>
            <td style="padding: 12px; vertical-align: middle;">{tool}</td>
            <td style="padding: 12px; vertical-align: middle;"><code>{lang}</code></td>
            <td style="padding: 12px; vertical-align: middle;">{loc}</td>
            <td style="padding: 12px; vertical-align: middle; font-weight: 600;">{cwes_found}</td>
            <td style="padding: 12px; vertical-align: middle; text-align: center; font-weight: 500; color: #cf222e;">{r.get('h', 0)}</td>
            <td style="padding: 12px; vertical-align: middle; text-align: center; font-weight: 500; color: #d4a724;">{r.get('m', 0)}</td>
            <td style="padding: 12px; vertical-align: middle; text-align: center; font-weight: 500; color: #0969da;">{r.get('l', 0)}</td>
            <td style="padding: 12px; vertical-align: middle;">{issues_files}</td>
        </tr>"""

        if has_flaw and findings_list:
            body_html += f"""
            <tr id="{row_id}" class="details-row">
                <td colspan="13" style="padding: 20px 30px; background-color: #fff8f8; border-left: 4px solid #cf222e;">
                    <h4 style="margin-top: 0; margin-bottom: 10px;">📋 Discovered Weakness Deep-Dive Evidence (PR CWE Change Density: {r.get('density', 0.0)}):</h4>
                    <table class="details-table" style="width: 100%; border-collapse: collapse; font-size: 13px;">
                        <thead>
                            <tr>
                                <th style="width:15%; background: #eaecef; padding: 8px; text-align: left;">Security</th>
                                <th style="width:20%; background: #eaecef; padding: 8px; text-align: left;">Vulnerability Rule</th>
                                <th style="width:25%; background: #eaecef; padding: 8px; text-align: left;">File Location & Line</th>
                                <th style="width:40%; background: #eaecef; padding: 8px; text-align: left;">Defect Context Description</th>
                            </tr>
                        </thead>
                        <tbody>
                            {sub_table_rows}
                        </tbody>
                    </table>
                </td>
            </tr>"""

    footer_html = "</tbody></table></body></html>"
    
    with open(output_path, "w", encoding="utf-8") as out:
        out.write(header_html + body_html + footer_html)
    print(f"✨ SUCCESS: Consolidated HTML dashboard successfully generated at: {output_path}")

if __name__ == "__main__":
    main()
