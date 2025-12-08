import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime

url = "https://humanservices.arkansas.gov/divisions-shared-services/medical-services/helpful-information-for-providers/fee-schedules/"
response = requests.get(url)
soup = BeautifulSoup(response.content, 'html.parser')

pattern = re.compile(r"Physician")
link = None

trs = soup.find_all("tr")
found = False

for tr in trs:
    tds = tr.find_all("td")

    if len(tds) < 2:
        continue

    date_text = tds[0].get_text(strip=True)
    title_text = tds[1].get_text(strip=True)

    if pattern.match(title_text):
        for a in tds[1].find_all("a"):
            if a.get_text(strip=True).lower() == "pdf":
                link = a.get("href")
                break

            # if link:
            #     date_text = tds[0].get_text(strip=True)
            #     filename = f"AR_Fee_{formatted_date}.pdf"

            file_response = requests.get(link)
            with open(filename, "wb") as file:
                file.write(file_response.content)