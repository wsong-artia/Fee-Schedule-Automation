from playwright.sync_api import sync_playwright
from pathlib import Path

def main():
    download_dir = Path(__file__).resolve().parent

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()

        page.goto("https://hcpf.colorado.gov/provider-rates-fee-schedule")
        page.wait_for_load_state("networkidle")

        links = page.locator('a:has-text("PAD Fee Schedule")')
        if links.count() == 0:
            browser.close()
            return

        with page.expect_download() as d:
            links.nth(0).click()

        download = d.value
        download.save_as(download_dir / download.suggested_filename)

        browser.close()

main()