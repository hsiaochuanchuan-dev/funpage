r"""
generate_brokerage.py — Generate brokerage pages from Google Sheets
===============================================================
Reads the Google Sheet range A1:E12 from OtherNote › sheet 'brokerage',
then writes a public page at both index.html and brokerage.html.

SETUP
-----
1. Enable Google Sheets API in Google Cloud Console.
2. Create a Service Account and download the JSON key.
3. Share the spreadsheet with the service account email.
4. Save the key as: C:\Users\USER\Documents\Claude\Projects\FunPage\service_account.json
5. Install dependencies:
     pip install gspread

RUN
---
    python generate_brokerage.py
"""
import html
from pathlib import Path
from datetime import datetime

SPREADSHEET_ID = '1pljY-of-ICBP8WQVgg8l5ICSpL3F6rMs3B8XJXdP2t4'
SHEET_NAME = 'brokerage'
RANGE = 'A1:E12'
CREDS_FILE = Path(__file__).parent / 'service_account.json'
OUTPUT_FILE = Path(__file__).parent / 'brokerage.html'
ROOT_FILE = Path(__file__).parent / 'index.html'


def build_html(rows):
    title = 'Brokerage Ranking'
    updated_at = datetime.now().strftime('%Y/%m/%d %H:%M')
    header_cells = rows[0] if rows else ['Code', 'Name', 'Reason', 'Action', 'Notes']
    body_rows = rows[1:] if len(rows) > 1 else []

    def td(value, header=False):
        tag = 'th' if header else 'td'
        return f'<{tag}>{html.escape(str(value))}</{tag}>'

    header_html = ''.join(td(cell, header=True) for cell in header_cells)
    body_html = ''
    if body_rows:
        for row in body_rows:
            row_cells = [td(cell) for cell in row] + [''] * max(0, len(header_cells) - len(row))
            body_html += f'<tr>{"".join(row_cells)}</tr>\n'
    else:
        body_html = (
            '<tr><td colspan="5" style="text-align:center; padding: 24px;">'
            'No data available. Verify your Google Sheet and run <code>python generate_brokerage.py</code>.</td></tr>\n'
        )

    return f'''<!DOCTYPE html>
<html lang="zh-Hant">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
<header>
  <h1>{title}</h1>
  <sub>Data source: OtherNote › brokerage (A1:E12)</sub>
</header>
<div class="statusbar">
  <span class="dot"></span>
  <span>Last updated: {updated_at}</span>
</div>
<main>
  <div class="card">
    <div class="card-head">
      <h2>Brokerage Ranking</h2>
      <span>Google Sheets range {RANGE}</span>
    </div>
    <div class="tbl-wrap">
      <table>
        <thead>
          <tr>{header_html}</tr>
        </thead>
        <tbody>
{body_html}        </tbody>
      </table>
    </div>
  </div>
</main>
<footer>
  Published as a GitHub Pages page at <code>https://hsiaochuanchuan-dev.github.io/brokerage</code> when deployed from the repository root.
</footer>
</body>
</html>'''


def fetch_sheet_rows():
    try:
        import gspread
    except ImportError:
        raise RuntimeError('Missing dependency: pip install gspread')

    if not CREDS_FILE.exists():
        raise RuntimeError(
            f'Service account credentials not found at {CREDS_FILE}.\n'
            'See the SETUP section in generate_brokerage.py.'
        )

    gc = gspread.service_account(filename=str(CREDS_FILE))
    sh = gc.open_by_key(SPREADSHEET_ID)
    ws = sh.worksheet(SHEET_NAME)
    return ws.get(RANGE)


def main():
    try:
        rows = fetch_sheet_rows()
        page = build_html(rows)
        OUTPUT_FILE.write_text(page, encoding='utf-8')
        ROOT_FILE.write_text(page, encoding='utf-8')
        print(f'✓ Generated {OUTPUT_FILE.name} and {ROOT_FILE.name} from {SHEET_NAME} {RANGE}')
    except Exception as exc:
        print('ERROR:', exc)
        # Generate placeholder page when credentials are missing
        page = build_html([])
        OUTPUT_FILE.write_text(page, encoding='utf-8')
        ROOT_FILE.write_text(page, encoding='utf-8')
        print(f'✓ Generated placeholder {OUTPUT_FILE.name} and {ROOT_FILE.name} (run with valid credentials to load data)')


if __name__ == '__main__':
    main()
