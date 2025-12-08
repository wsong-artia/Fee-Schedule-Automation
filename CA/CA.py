from pathlib import Path
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright

PAGE = "https://mcweb.apps.prd.cammis.medi-cal.ca.gov/rates?tab=rates"
TARGET_NAME_IN_ZIP = "rates_data.xlsx"

def most_recent_fifteenth(now: datetime) -> datetime:
    """Return the most recent 15th of the month based on the current date."""
    this_month_16 = now.replace(day=15)
    if now.day >= 15:
        return this_month_16

    first_of_this_month = now.replace(day=1)
    last_day_prev_month = first_of_this_month - timedelta(days=1)
    prev_month_15 = last_day_prev_month.replace(day=15)
    return prev_month_15

def main():
    now = datetime.now()
    run_date = most_recent_fifteenth(now)
    out_filename = f"CA_Fee_{run_date.strftime('%m-%d-%Y')}.xlsx"
    OUT = Path(__file__).resolve().parent / out_filename

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(accept_downloads=True)
        page = ctx.new_page()
        page.goto(PAGE, wait_until="networkidle")

        with page.expect_download() as dl_info:
            page.get_by_role("link", name="Download All Medi-Cal Rates").click()
        download = dl_info.value

        zip_path = Path(__file__).resolve().parent / "zips" / (download.suggested_filename or "medi-cal.zip")
        zip_path.parent.mkdir(exist_ok=True)
        download.save_as(str(zip_path))

        import zipfile
        with zipfile.ZipFile(zip_path, "r") as zf:
            names = zf.namelist()
            name = TARGET_NAME_IN_ZIP if TARGET_NAME_IN_ZIP in names else next(n for n in names if n.lower().endswith(".xlsx"))
            with zf.open(name, "r") as src, open(OUT, "wb") as dst:
                dst.write(src.read())

                ctx.close()
        browser.close()

    print(f"[OK] Saved: {OUT}")

if __name__ == "__main__":
    main()
    exit(0)