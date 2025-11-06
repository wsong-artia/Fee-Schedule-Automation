import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime
import os

url = "https://azahcccs.gov/PlansProviders/RatesAndBilling/FFS/PhysicianAdministeredDrug.html"

def get_most_recent_file_url(page_url):
    response = requests.get(page_url)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')

    # Regex to find "Rates Effective [Month day, year]" in link text or href
    pattern = re.compile(r'Rates Effective ([A-Za-z]+ \d{1,2}, \d{4})', re.IGNORECASE)

    files = []
    for link in soup.find_all('a', href=True):
        text = link.get_text()
        href = link['href']
        match = pattern.search(text) or pattern.search(href)
        if match:
            date_str = match.group(1)
            try:
                date_obj = datetime.strptime(date_str, "%B %d, %Y")
                files.append((date_obj, href))
            except ValueError:
                continue

    if not files:
        raise ValueError("No files with 'Rates Effective [Month day, year]' found on the page.")

    # Find the file with the most recent date
    most_recent = max(files, key=lambda x: x[0])
    most_recent_date, file_url = most_recent

    # Make sure the file_url is absolute
    if not file_url.startswith('http'):
        file_url = requests.compat.urljoin(page_url, file_url)

    return most_recent_date, file_url

def download_file(file_url, save_folder='AZ', custom_filename=None):
    os.makedirs(save_folder, exist_ok=True)
    if custom_filename:
        local_filename = custom_filename
    else:
        local_filename = file_url.split('/')[-1]
    local_path = os.path.join(save_folder, local_filename)

    with requests.get(file_url, stream=True) as r:
        r.raise_for_status()
        with open(local_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)

    return local_path

if __name__ == "__main__":
    try:
        date, file_url = get_most_recent_file_url(url)
        print(f"Most recent file date: {date.strftime('%Y-%m-%d')}")
        print(f"Downloading file from: {file_url}")

        # Format filename as AZ_Fee_MM-DD-YYYY.xlsx
        filename_date_part = date.strftime("%m-%d-%Y")
        custom_filename = f"AZ_Fee_{filename_date_part}.xlsx"

        saved_path = download_file(file_url, custom_filename=custom_filename)
        print(f"File saved to: {saved_path}")
    except Exception as e:
        print(f"Error: {e}")
