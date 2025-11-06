import re
import requests
from bs4 import BeautifulSoup

url = "https://humanservices.arkansas.gov/divisions-shared-services/medical-services/helpful-information-for-providers/fee-schedules/"
response = requests.get(url)
soup = BeautifulSoup(response.content, 'html.parser')

pattern = re.compile(r"Physician")
link = None

trs = soup.find_all("tr")

for tr in trs:
    tds = tr.find_all("td")
    
    if len(tds) < 4:
        continue
    
    title_text = tds[0].get_text(strip=True)
    
    if pattern.match(title_text):
        for a in tds[2].find_all("a"):  
            if a.get_text(strip=True).lower() == "pdf":
                link = a.get("href")
                break
    
        if link:
            date_text = tds[3].get_text(strip=True)
            filename = f"AR_Fee_{date_text.replace('/', '-')}.pdf"
            file_response = requests.get(link)
            with open(filename, 'wb') as file:
                file.write(file_response.content)