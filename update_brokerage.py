"""
update_brokerage.py — 富邦嘉義分點 當沖排行自動寫入
======================================================
抓取富邦嘉義分點買超排行，分析前10支適合當沖股票，
寫入 OtherNote → sheet 'brokerage'。

SETUP（一次性設定）
-------------------
1. Google Cloud Console:
   - 建立專案 → 啟用 Sheets API + Drive API
   - 建立 Service Account → 下載 JSON 金鑰
   - 將 OtherNote 試算表與 Service Account email 共用（Editor 權限）
2. 儲存金鑰至：
     C:\\Users\\USER\\Documents\\Claude\\Projects\\FunPage\\service_account.json
3. 安裝套件：
     pip install gspread requests --break-system-packages

執行：
     python update_brokerage.py
"""

import re
import urllib.request
from pathlib import Path
from datetime import date

# ── 設定 ──────────────────────────────────────────────────────────────────
SPREADSHEET_ID = '1pljY-of-ICBP8WQVgg8l5ICSpL3F6rMs3B8XJXdP2t4'
SHEET_NAME     = 'brokerage'
CREDS_FILE     = Path(__file__).parent / 'service_account.json'
BROKER_URL     = 'https://fubon-ebrokerdj.fbs.com.tw/z/zg/zgb/zgb0.djhtm?a=9600&b=9692&c=E&d=1'
# ─────────────────────────────────────────────────────────────────────────


def fetch_buy_excess():
    """抓取富邦嘉義分點買超排行，回傳 (query_date, list of (code,name,buy,sell,diff))"""
    req = urllib.request.Request(BROKER_URL, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=15) as resp:
        raw = resp.read()
    html = raw.decode('big5', errors='replace')

    # 查詢日期
    date_m = re.search(r'最新資料日期:(\d+)', html)
    raw_date = date_m.group(1) if date_m else date.today().strftime('%Y%m%d')
    query_date = f"{raw_date[:4]}/{raw_date[4:6]}/{raw_date[6:]}"

    # 解析每一行
    row_pat = re.compile(
        r'<td class="t4t1"[^>]*>.*?(?:GenLink2stk\(\'AS(\d+)\',\'([^\']+)\'\)'
        r'|Link2Stk\(\'([^\']+)\'\).*?">([^<]+)</a>).*?</td>\s*'
        r'<td class="t3n1"[^>]*>([\d,]+)</td>\s*'
        r'<td class="t3n1"[^>]*>([\d,]+)</td>\s*'
        r'<td class="t3n1"[^>]*>([\d,\-]+)</td>',
        re.DOTALL
    )
    results = []
    for r in row_pat.findall(html):
        as_code, as_name, href_code, href_name, buy, sell, diff = r
        code = as_code if as_code else href_code
        name = as_name if as_name else href_name
        diff_v = int(diff.replace(',', ''))
        if diff_v > 0:  # 只取買超
            results.append((code, name, int(buy.replace(',','')),
                            int(sell.replace(',','')), diff_v))
    return query_date, results


def select_top10(stocks):
    """從個股（非ETF）買超中挑選最適合當沖的前10支"""
    individuals = [(c,n,b,s,d) for c,n,b,s,d in stocks if re.match(r'^\d{4}$', c)]

    # 分析重點：差額為主，總量為輔，兼顧差額率
    def score(item):
        c, n, b, s, d = item
        total = b + s
        ratio = d / total if total > 0 else 0
        # 高差額 + 高總量 + 高差額率的加權分數
        return d * 0.6 + total * 0.03 + ratio * 500

    ranked = sorted(individuals, key=score, reverse=True)

    # 套用當沖理由與操作重點（依股票代號特性）
    sector_map = {
        '2303': ('晶圓代工', '站穩5日線做多，停損前日低點，目標前波高點'),
        '2408': ('DRAM記憶體', '突破前日高追進，支撐前日低，注意美股記憶體連動'),
        '1785': ('材料-高總量', '純技術操作，1分鐘K突破切入，快進快出1-2%停損'),
        '2409': ('面板龍頭', '突破前高追進，面板易跳空，進場即設停損'),
        '3714': ('LED晶片', '開高走高順勢做多，9:30後量縮整理切入'),
        '3006': ('IC設計', '量縮回測均線買進，放量突破加碼，2%停損'),
        '2426': ('LED晶片', '富采強時跟進補漲，倉位50%以下'),
        '2491': ('主力鎖籌', '股本小，倉位不宜重，3%緊停損，快進快出'),
        '5347': ('晶圓代工', '聯電強時跟進，放量突破前高追入'),
        '6182': ('矽晶圓', '整理後放量突破做多，小倉試單'),
    }

    top10 = []
    for c, n, b, s, d in ranked[:10]:
        total = b + s
        ratio = d / total * 100 if total > 0 else 0
        sector, op_hint = sector_map.get(c, ('個股', '順勢操作，嚴守停損'))
        reason = (f"{sector}族群，分點淨買超{d:,}張，"
                  f"總量{total:,}張，差額率{ratio:.1f}%，"
                  f"富邦嘉義分點積極布局，籌碼集中。")
        top10.append((c, n, reason, op_hint))
    return top10


def write_to_sheet(query_date, top10):
    try:
        import gspread
    except ImportError:
        print("ERROR: 請先執行 pip install gspread")
        return False

    if not CREDS_FILE.exists():
        print(f"ERROR: 找不到 {CREDS_FILE}")
        print("請參照 update_dividends.py 的 SETUP 說明設定 Service Account。")
        return False

    print(f"連線 Google Sheets… ({SPREADSHEET_ID})")
    gc = gspread.service_account(filename=str(CREDS_FILE))
    sh = gc.open_by_key(SPREADSHEET_ID)
    ws = sh.worksheet(SHEET_NAME)

    # B1 = 查詢日期
    ws.update('B1', query_date)
    print(f"  ✓ B1 = {query_date}")

    # 清除 B3:F12
    ws.batch_clear(['B3:F12'])

    # 寫入 B3:E12
    data = [[c, n, reason, op] for c, n, reason, op in top10]
    ws.update('B3', data)
    print(f"  ✓ B3:F12 寫入 {len(data)} 行")
    print("\n全部更新完成。")
    return True


def main():
    print("=== 富邦嘉義分點 當沖排行 ===")
    query_date, stocks = fetch_buy_excess()
    print(f"資料日期: {query_date}  買超個股數: {len(stocks)}")

    top10 = select_top10(stocks)
    print(f"\n前10支當沖推薦：")
    for i, (c, n, reason, op) in enumerate(top10, 1):
        print(f"  #{i} {c} {n}")
        print(f"      原因: {reason[:50]}…")
        print(f"      操作: {op}")

    write_to_sheet(query_date, top10)


if __name__ == '__main__':
    main()
