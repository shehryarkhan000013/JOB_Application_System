"""
report_generator.py — Excel campaign analytics report generator.

Reads all leads from the database and produces a formatted Excel workbook
with two sheets: a full data table ('All Leads') and a visual pie-chart
dashboard ('Dashboard') showing the breakdown of pipeline statuses.
"""

import os
import pandas as pd
import src.database as database


def generate_excel_report(output_filename: str = "Campaign_Report.xlsx") -> None:
    """Generates a formatted Excel report from the current leads database.

    Creates an Excel workbook containing:
    - Sheet 1 ('All Leads'): Full table of all scraped leads with formatted
      headers and auto-adjusted column widths.
    - Sheet 2 ('Dashboard'): Status summary table and a pie chart showing
      the distribution of leads across pipeline stages.

    Args:
        output_filename: The name of the Excel file to write. Defaults to
                         'Campaign_Report.xlsx' in the project root.
    """
    print("Generating campaign report...")

    conn = database.get_connection()
    df = pd.read_sql_query("SELECT * FROM leads", conn)
    conn.close()

    if df.empty:
        print("[INFO] No leads in the database — nothing to report.")
        return

    status_counts = df['status'].value_counts()
    output_path = os.path.join(os.path.dirname(__file__), '..', output_filename)

    writer = pd.ExcelWriter(output_path, engine='xlsxwriter')

    # --- Sheet 1: All Leads ---
    df.to_excel(writer, sheet_name='All Leads', index=False)
    workbook = writer.book
    worksheet_data = writer.sheets['All Leads']

    header_format = workbook.add_format({
        'bold': True, 'text_wrap': True, 'valign': 'top',
        'fg_color': '#D7E4BC', 'border': 1
    })

    for col_num, value in enumerate(df.columns.values):
        worksheet_data.write(0, col_num, value, header_format)

    for i, col in enumerate(df.columns):
        col_width = max(df[col].astype(str).map(len).max(), len(col)) + 2
        worksheet_data.set_column(i, i, col_width)

    # --- Sheet 2: Dashboard with pie chart ---
    worksheet_summary = workbook.add_worksheet('Dashboard')
    worksheet_summary.write('A1', 'Status', header_format)
    worksheet_summary.write('B1', 'Count', header_format)

    for row, (status, count) in enumerate(status_counts.items(), start=1):
        worksheet_summary.write(row, 0, status)
        worksheet_summary.write(row, 1, count)

    max_row = len(status_counts)
    chart = workbook.add_chart({'type': 'pie'})
    chart.add_series({
        'name':       'Campaign Progress',
        'categories': ['Dashboard', 1, 0, max_row, 0],
        'values':     ['Dashboard', 1, 1, max_row, 1],
        'data_labels': {'value': True, 'percentage': True},
    })
    chart.set_title({'name': 'Automated Applications — Pipeline Status'})
    worksheet_summary.insert_chart('D2', chart)

    writer.close()
    print(f"[SUCCESS] Report saved: {output_path}")


if __name__ == '__main__':
    generate_excel_report()
