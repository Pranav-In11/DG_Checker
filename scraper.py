import os
import sys
import requests
from bs4 import BeautifulSoup
import random
import time

# --- SAFETY FIX ---
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# --- CONFIGURATION ---
EMAIL = os.getenv('USER_EMAIL')
PASSWORD = os.getenv('USER_PASSWORD')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

LOGIN_URL = "http://220.156.188.226/CREBS/"

# SOURCE 1: Proxyscrape API
URL_SOURCE_1 = "https://api.proxyscrape.com/v4/free-proxy-list/get?request=display_proxies&country=in&proxy_format=protocolipport&format=text&timeout=20000"

# SOURCE 2: Proxifly GitHub (Raw Text)
URL_SOURCE_2 = "https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/countries/IN/data.txt"

# --- FUNCTIONS ---

def get_proxies_source_1():
    """Fetch from Proxyscrape"""
    print("🌍 Fetching Source 1 (Proxyscrape)...")
    try:
        r = requests.get(URL_SOURCE_1, timeout=10)
        if r.status_code == 200:
            proxies = [line.strip() for line in r.text.split('\n') if line.strip()]
            print(f"   ✅ Source 1 found {len(proxies)} proxies.")
            return proxies
    except Exception as e:
        print(f"   ❌ Source 1 failed: {e}")
    return []

def get_proxies_source_2():
    """Fetch from Proxifly (GitHub)"""
    print("🌍 Fetching Source 2 (Proxifly)...")
    try:
        r = requests.get(URL_SOURCE_2, timeout=10)
        if r.status_code == 200:
            # GitHub list lines are like "http://ip:port" or "socks5://ip:port"
            proxies = [line.strip() for line in r.text.split('\n') if line.strip()]
            print(f"   ✅ Source 2 found {len(proxies)} proxies.")
            return proxies
    except Exception as e:
        print(f"   ❌ Source 2 failed: {e}")
    return []

def send_telegram(message):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID: return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}, timeout=10)
    except: pass

def attempt_scrape_with_proxy(proxy_url, attempt_num):
    print(f"   👉 [Attempt {attempt_num}] Trying: {proxy_url} ...")
    
    session = requests.Session()
    # Support for http, https, socks4, socks5 based on the URL prefix
    session.proxies = {"http": proxy_url, "https": proxy_url}
    
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'http://220.156.188.226/CREBS/'
    })

    try:
        # 1. Test Connection (Short timeout to skip bad proxies fast)
        r_get = session.get(LOGIN_URL, timeout=10)
        if r_get.status_code != 200: return False, "Page load failed"

        # 2. Login
        payload = {'txtEmail': EMAIL, 'txtPassword': PASSWORD, 'returnUrl': ''}
        r_post = session.post(LOGIN_URL, data=payload, timeout=15)

        # 3. Validate
        if "Signout" in r_post.text or "Welcome" in r_post.text:
            return True, r_post.text
        else:
            return False, "Login failed"

    except Exception as e:
        return False, str(e)

def parse_and_notify(html_content):
    soup = BeautifulSoup(html_content, 'lxml')
    data_cells = soup.find_all('td', class_='tablebodytext')
    
    results = []
    for i in range(0, len(data_cells), 4):
        group = data_cells[i:i+4]
        if len(group) == 4:
            results.append({
                'paper': group[0].get_text(strip=True),
                'type': group[1].get_text(strip=True),
                'date': group[2].get_text(strip=True),
                'status': group[3].get_text(strip=True)
            })

    if results:
        print(f"📊 Parsed {len(results)} results.")
        message = "📢 <b>CREBS Result Update</b>\n\n"
        has_update = False
        for res in results:
            icon = "✅" if "pass" in res['status'].lower() else "❌"
            msg_line = f"{icon} <b>{res['paper']}</b>\nStatus: <b>{res['status']}</b>\n\n"
            message += msg_line
            has_update = True
        
        if has_update:
            send_telegram(message)
            print("✅ Telegram sent.")
    else:
        print("🤷 Login worked, but no results found.")

def run():
    print("--- Starting Multi-Source Scraper ---")
    
    # 1. Get Lists from BOTH sources
    list1 = get_proxies_source_1()
    list2 = get_proxies_source_2()
    
    # 2. Combine and Remove Duplicates (using set)
    all_proxies = list(set(list1 + list2))
    
    if not all_proxies:
        print("❌ No proxies found from any source. Exiting.")
        sys.exit(1)

    print(f"🔥 Total unique proxies available: {len(all_proxies)}")

    # 3. Randomize
    random.shuffle(all_proxies)

    # 4. Try top 30 proxies
    success = False
    for i, proxy in enumerate(all_proxies[:30]):
        is_success, html = attempt_scrape_with_proxy(proxy, i+1)
        if is_success:
            print("🎉 SUCCESS! Connection established.")
            parse_and_notify(html)
            success = True
            break
            
    if not success:
        print("❌ All attempts failed.")
        sys.exit(1)

if __name__ == "__main__":
    run()
