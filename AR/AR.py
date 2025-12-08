import sys
import re
from datetime import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeoutError

FEE_SCHEDULES_URL = "https://humanservices.arkansas.gov/divisions-shared-services/medical-services/helpful-information-for-providers/fee-schedules/"

def normalize_run_date(date_text: str) -> str:
    date_text = date_text.strip()
    for fmt in ("%m/%d/%y", "%m/%d/%Y", "%m-%d-%y", "%m-%d-%Y"):
        try:
            dt = datetime.strptime(date_text, fmt)
            if dt.year < 2000:
                dt = dt.replace(year=2000 + dt.year - 1900)
            return dt.strftime("%m-%d-%Y")
        except ValueError:
            continue
    try:
        dt = datetime.fromisoformat(date_text)
        return dt.strftime("%m-%d-%Y")
    except Exception:
        return datetime.now().strftime("%m-%d-%Y")

def main() -> int:
    base_dir = Path(__file__).resolve().parent

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()

        page.goto(FEE_SCHEDULES_URL, wait_until="networkidle")

        rows = page.locator("table tr")
        count = rows.count()
        if count == 0:
            print("[ERROR] No table rows found; the page structure may have changed.")
            context.close(); browser.close()
            return 2

        physician_row_index = None
        run_date_text = None
        pdf_link = None

        for i in range(count):
            row = rows.nth(i)
            tds = row.locator("td")
            if tds.count() < 2:
                continue

            # First td: Run Date; Second td: Fee Schedule name + link(s)
            run_date_text = tds.nth(0).inner_text().strip()
            title_text = tds.nth(1).inner_text().strip()

            if re.search(r"\bPhysician\b", title_text, flags=re.IGNORECASE):
                physician_row_index = i
                # Look for 'PDF' link inside second td
                # Try an <a> whose text is exactly 'PDF'
                links = tds.nth(1).locator("a")
                for j in range(links.count()):
                    a = links.nth(j)
                    link_text = a.inner_text().strip().lower()
                    href = a.get_attribute("href") or ""
                    if link_text == "pdf" or href.lower().endswith(".pdf"):
                        pdf_link = a
                        break
                break

        if physician_row_index is None or pdf_link is None:
            print("[ERROR] Could not find 'Physician' row or its PDF link.")
            context.close(); browser.close()
            return 2

        try:
            with page.expect_download(timeout=30000) as dl_info:
                pdf_link.click()
            download = dl_info.value
        except PWTimeoutError:
            print("[ERROR] Timeout waiting for the PDF download.")
            context.close(); browser.close()
            return 2

        formatted_date = normalize_run_date(run_date_text)
        out_name = f"AR_Fee_{formatted_date}.pdf"
        out_path = base_dir / out_name

        suggested = download.suggested_filename or out_name
        download.save_as(str(out_path))

        print(f"[OK] Saved: {out_path}")
        context.close(); browser.close()

    return 0

if __name__ == "__main__":
    sys.exit(main())