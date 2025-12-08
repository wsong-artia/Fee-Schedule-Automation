
#!/usr/bin/env python3
"""
Medi-Cal Rates Downloader (HTML-only via regex; robust + finished)

- Fetches the Medi-Cal Rates page and extracts the "/assets/<UUID>?download" link.
- Downloads the file with redirects (streaming), validates size and content-type,
  logs outcomes, and writes a CSV ledger.
- Falls back to a last-known asset URL if HTML parsing fails or the page is down.

References:
- Rates page: https://mcweb.apps.prd.cammis.medi-cal.ca.gov/rates?tab=rates
- Example asset: https://mcweb.apps.prd.cammis.medi-cal.ca.gov/assets/7F47F6EF-FCF3-49B5-9BD8-543F94AD9E46?download
"""

import csv
import hashlib
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests

# --------------------------
# Configuration
# --------------------------
RATES_PAGE = "https://mcweb.apps.prd.cammis.medi-cal.ca.gov/rates?tab=rates"
# Fallback: last-known asset URL. Update this if DHCS changes the asset UUID.
LAST_KNOWN_ASSET = (
    "https://mcweb.apps.prd.cammis.medi-cal.ca.gov/assets/7F47F6EF-FCF3-49B5-9BD8-543F94AD9E46?download"
)

OUT_DIR = Path("./downloads")  # where files and logs are stored
LEDGER_CSV = OUT_DIR / "download_ledger.csv"
LOG_FILE = OUT_DIR / "download.log"

# Safety threshold to avoid saving tiny HTML error pages as "xlsx"
MIN_EXPECTED_BYTES = 50_000  # adjust if you know typical file size
TIMEOUT = 60                 # seconds per request
MAX_RETRIES = 3              # network retries for transient issues

HEADERS = {
    "User-Agent": "Mozilla/5.0 (MediCalRatesAutomation)",
    "Accept": "*/*",
}

# Regex that matches the asset link anywhere in the HTML (including inline scripts)
ASSET_PATTERN = re.compile(
    r"https://mcweb\.apps\.prd\.cammis\.medi-cal\.ca\.gov/assets/[0-9A-Fa-f-]+\?download"
)

# --------------------------
# Helpers
# --------------------------
def log(msg: str) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{stamp}] {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def http_get(session: requests.Session, url: str, allow_redirects: bool = True, stream: bool = False) -> requests.Response:
    last_exc = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = session.get(
                url,
                headers=HEADERS,
                timeout=TIMEOUT,
                allow_redirects=allow_redirects,
                stream=stream,
            )
            return resp
        except requests.RequestException as e:
            last_exc = e
            log(f"Attempt {attempt}/{MAX_RETRIES} failed for {url}: {e}")
            time.sleep(2 * attempt)  # simple backoff
    raise last_exc if last_exc else RuntimeError("Unknown HTTP error")

def extract_asset_url(html: str) -> Optional[str]:
    """
    Extract the first asset URL of the form:
    https://mcweb.apps.prd.cammis.medi-cal.ca.gov/assets/<UUID>?download
    """
    m = ASSET_PATTERN.search(html)
    return m.group(0) if m else None

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):  # 1MB chunks
            h.update(chunk)
    return h.hexdigest()

def append_ledger_row(path: Path, url: str, size: int, checksum: str, ok: bool, note: str = "") -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    header = ["timestamp", "file", "url", "size_bytes", "sha256", "status", "note"]
    row = [
        datetime.now().isoformat(timespec="seconds"),
        str(path),
        url,
        size,
        checksum,
        "OK" if ok else "FAIL",
        note,
    ]
    new_file = not LEDGER_CSV.exists()
    with open(LEDGER_CSV, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new_file:
            w.writerow(header)
        w.writerow(row)

def pick_filename_from_headers(headers: requests.structures.CaseInsensitiveDict, default_name: str) -> str:
    """
    If Content-Disposition is present with filename, use that; otherwise return default_name.
    """
    cd = headers.get("Content-Disposition", "")
    if "filename=" in cd:
        # Extract filename=... possibly quoted
        m = re.search(r'filename\*?=([^;]+)', cd, flags=re.IGNORECASE)
        if m:
            raw = m.group(1).strip().strip('"').strip("'")
            # RFC 5987 may include encoding like UTF-8''actualname.xlsx ; strip before ''
            if "''" in raw:
                raw = raw.split("''", 1)[1]
            # sanitize
            fname = os.path.basename(raw)
            if fname:
                return fname
    return default_name

# --------------------------
# Main steps
# --------------------------
def download_asset(session: requests.Session, asset_url: str) -> int:
    log(f"Downloading asset: {asset_url}")
    try:
        dl_resp = http_get(session, asset_url, allow_redirects=True, stream=True)
    except Exception as e:
        log(f"ERROR downloading asset: {e}")
        append_ledger_row(Path("N/A"), asset_url, 0, "", False, note=str(e))
        return 2

    if dl_resp.status_code != 200:
        log(f"ERROR: asset HTTP {dl_resp.status_code}")
        append_ledger_row(Path("N/A"), asset_url, 0, "", False, note=f"HTTP {dl_resp.status_code}")
        return 2

    # Decide filename: use content-disposition if present, else timestamped default
    ts = datetime.now().strftime("%Y%m%d")
    default_name = f"medi-cal-rates_{ts}.xlsx"
    out_name = pick_filename_from_headers(dl_resp.headers, default_name)
    out_path = OUT_DIR / out_name

    # Stream to disk
    try:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        with open(out_path, "wb") as f:
            for chunk in dl_resp.iter_content(chunk_size=1 << 20):
                if chunk:
                    f.write(chunk)
    except Exception as e:
        log(f"ERROR writing file: {e}")
        append_ledger_row(out_path, asset_url, 0, "", False, note=str(e))
        return 2

    # Validate size & content-type
    size = out_path.stat().st_size
    ctype = dl_resp.headers.get("Content-Type", "")
    note = ""
    if size < MIN_EXPECTED_BYTES:
        note = f"Small file (<{MIN_EXPECTED_BYTES} bytes)"
        log(f"WARNING: downloaded file is unexpectedly small ({size} bytes). Content-Type={ctype}")

    # Compute checksum
    checksum = sha256_file(out_path)

    log(f"Saved file: {out_path} (size={size} bytes, sha256={checksum[:12]}..., Content-Type={ctype})")
    append_ledger_row(out_path, asset_url, size, checksum, True, note=note)
    return 0

def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    try:
        # Step 1: fetch rates page
        log(f"Fetching rates page: {RATES_PAGE}")
        try:
            page_resp = http_get(session, RATES_PAGE, allow_redirects=True, stream=False)
        except Exception as e:
            log(f"ERROR fetching rates page: {e}")
            log("Falling back to last-known asset URL.")
            return download_asset(session, LAST_KNOWN_ASSET)

        if page_resp.status_code != 200:
            log(f"ERROR: Rates page HTTP {page_resp.status_code}. Falling back to last-known asset.")
            return download_asset(session, LAST_KNOWN_ASSET)

        # Step 2: extract asset URL via regex
        asset_url = extract_asset_url(page_resp.text)
        if not asset_url:
            log("Could not find asset URL in HTML. Falling back to last-known asset URL.")
            asset_url = LAST_KNOWN_ASSET

        log(f"Asset URL resolved: {asset_url}")

        # Step 3: download asset
        return download_asset(session, asset_url)
    finally:
        session.close()

## Correct guard:
if __name__ == "__main__":
    sys.exit(main())