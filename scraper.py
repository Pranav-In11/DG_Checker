import os
import sys
import json
import time
import random
import requests
from bs4 import BeautifulSoup

# --- CONFIGURATION (Reads from GitHub Secrets) ---
EMAIL = os.getenv('USER_EMAIL')
PASSWORD = os.getenv('USER_PASSWORD')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

BASE_URL = "http://220.156.188.226/CREBS/"
URL_BOOKING = "http://220.156.188.226/CREBS/Booking/BookingList"
HISTORY_FILE = "scrape_history.json"

# Proxy Sources
URL_SOURCE_1 = "https://api.proxyscrape.com/v4/free-proxy-list/get?request=display_proxies&country=in&proxy_format=protocolipport&format=text&timeout=20000"
URL_SOURCE_2 = "https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/countries/IN/data.txt"

def get_proxies():
    """Combines proxies from multiple sources"""
    proxies = []
    for url in [URL_SOURCE_1, URL_SOURCE_2]:
        try:
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                proxies.extend([line.strip() for line in r.text.split('\n') if line.strip()])
        except: pass
    return list(set(proxies))

def send_telegram(message):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID: return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}, timeout=10)
    except Exception as e:
        print(f"Telegram failed: {e}")

def scrape_data(proxy_url):
    """Logs in and pulls HTML from both Results and Booking pages"""
    session = requests.Session()
    session.proxies = {"http": proxy_url, "https": proxy_url}
    session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})

    # 1. Login
    payload = {'txtEmail': EMAIL, 'txtPassword': PASSWORD, 'returnUrl': ''}
    res = session.post(BASE_URL, data=payload, timeout=20)
    
    if "Signout" not in res.text:
        return None

    # 2. Get Results (from Home/Landing page)
    results_html = res.text
    
    # 3. Get Bookings
    booking_html = session.get(URL_BOOKING, timeout=20).text
    
    return {"results": results_html, "bookings": booking_html}

def parse_and_compare(data_dict):
    current_state = {}

    # Parse Results Table
    soup_res = BeautifulSoup(data_dict['results'], 'lxml')
    res_cells = soup_res.find_all('td', class_='tablebodytext')
    for i in range(0, len(res_cells), 4):
        group = res_cells[i:i+4]
        if len(group) == 4:
            paper = group[0].get_text(strip=True)
            status = group[3].get_text(strip=True)
            current_state[f"RES_{paper}"] = status

    # Parse Bookings Table (For Dates and "Under Process")
    soup_book = BeautifulSoup(data_dict['bookings'], 'lxml')
    b_table = soup_book.find('table', id='SeatBookingListView_tblListView')
    if b_table:
        for row in b_table.find_all('tr')[1:]:
            cells = row.find_all('td', class_='tablebodytext')
            if len(cells) >= 5:
                paper = cells[0].get_text(strip=True)
                status = cells[2].get_text(strip=True)
                date = cells[3].get_text(strip=True)
                remarks = cells[4].get_text(strip=True)
                
                # Logic for Oral exam under process
                display_date = date if date != "-" else remarks
                current_state[f"BOOK_{paper}"] = f"{status} | {display_date}"

    # --- Change Detection ---
    try:
        with open(HISTORY_FILE, "r") as f:
            old_state = json.load(f)
    except:
        old_state = {}

    if current_state == old_state:
        print("😴 No changes found.")
        return

    # Build Change Message
    changes = []
    for key, val in current_state.items():
        if key not in old_state or old_state[key] != val:
            icon = "📊" if "RES_" in key else "📅"
            label = "RESULT" if "RES_" in key else "BOOKING"
            paper_name = key.replace("RES_", "").replace("BOOK_","")
            changes.append(f"{icon} <b>{label}: {paper_name}</b>\nNew: <code>{val}</code>")

    if changes:
        send_telegram("🔔 <b>CREBS UPDATE DETECTED!</b>\n\n" + "\n\n".join(changes))
        with open(HISTORY_FILE, "w") as f:
            json.dump(current_state, f)
        print("🚀 Notification sent!")

def run():
    print("🔄 Starting Scraper...")
    all_proxies = get_proxies()
    random.shuffle(all_proxies)
    
    for i, proxy in enumerate(all_proxies[:20]):
        print(f"  Trying proxy {i+1}: {proxy}")
        try:
            data = scrape_data(proxy)
            if data:
                parse_and_compare(data)
                return # Success
        except Exception as e:
            print(f"  Error: {e}")
    
    print("❌ All proxies failed or login invalid.")

if __name__ == "__main__":
    run()
