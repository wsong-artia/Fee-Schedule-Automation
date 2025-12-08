import re
from datetime import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeoutError

PAGE = "https://medicaid.alabama.gov/content/Gated/7.3G_Fee_Schedules.aspx"

BASE_DIR = Path(__file__).resolve().parent
OUT_DIR = BASE_DIR
OUT_NAME = f"AL_Fee_{datetime.now().strftime('%m-%d-%Y')}.xlsx"
OUT_PATH = OUT_DIR / OUT_NAME

AGREE_LABELS = [r"I Accept", r"I Agree", r"Accept"]
PHYSICIAN_EXCEL_LABELS = [
    r"Physician Fee Schedule \(Excel\)",
    r"Physician Drug Fee Schedule \(Excel\)",
    r"Physician.*Excel",
]

def click_agree(page):
    for label in AGREE_LABELS:
        try:
            page.get_by_role("button", name=re.compile(label, re.I)).click()
            return True
        except Exception:
            pass
    try:
        page.get_by_text(re.compile(r"(I\s*(Accept|Agree))", re.I)).first.click()
        return True
    except Exception:
        return False

def click_physician_excel(page):
    for label in PHYSICIAN_EXCEL_LABELS:
        try:
            locator = page.get_by_role("link", name=re.compile(label, re.I))
            with page.expect_download(timeout=30000) as dl_info:
                locator.click()
            return dl_info.value
        except PWTimeoutError:
            continue
        except Exception:
            continue
    links = page.locator("a")
    for i in range(links.count()):
        a = links.nth(i)
        text = a.inner_text().strip()
        href = a.get_attribute("href") or ""
        if re.search(r"physician", text, re.I) and re.search(r"\.xlsx(\b|$)", href, re.I):
            with page.expect_download(timeout=30000) as dl_info:
                a.click()
            return dl_info.value
    raise RuntimeError("Physician Excel link not found.")

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()
        page.goto(PAGE, wait_until="networkidle")

        click_agree(page)
        download = click_physician_excel(page)

        OUT_DIR.mkdir(parents=True, exist_ok=True)
        download.save_as(str(OUT_PATH))
        print(f"[OK] Saved: {OUT_PATH.resolve()}")

        context.close()
        browser.close()

if __name__ == "__main__":
    main()
    exit(0)