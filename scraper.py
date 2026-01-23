import os
import sys
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import random
import time

# Load environment variables
# --- SAFETY FIX ---
# This allows the script to run on GitHub Actions even if python-dotenv is missing
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # This means we are on GitHub Actions (or the library isn't installed).
    # We don't need .env files there because we use Secrets.
    pass

# --- CONFIGURATION ---
EMAIL = os.getenv('USER_EMAIL')
PASSWORD = os.getenv('USER_PASSWORD')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

LOGIN_URL = "http://220.156.188.226/CREBS/"
PROXY_API_URL = "https://api.proxyscrape.com/v4/free-proxy-list/get?request=display_proxies&country=in&proxy_format=protocolipport&format=text&timeout=20000"

# --- FUNCTIONS ---

def get_indian_proxies():
    """Fetches a fresh list of Indian proxies from ProxyScrape."""
    print("🌍 Fetching fresh Indian proxies...")
    try:
        r = requests.get(PROXY_API_URL, timeout=10)
        if r.status_code == 200:
            # The API returns one proxy per line like 'http://1.2.3.4:8080'
            proxies = [line.strip() for line in r.text.split('\n') if line.strip()]
            print(f"✅ Found {len(proxies)} Indian proxies.")
            return proxies
    except Exception as e:
        print(f"❌ Failed to fetch proxy list: {e}")
    return []

def send_telegram(message):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}, timeout=10)
    except:
        pass

def attempt_scrape_with_proxy(proxy_url, attempt_num):
    """Tries to login and scrape using a specific proxy."""
    
    # Format the proxy dictionary
    proxies = {
        "http": proxy_url,
        "https": proxy_url
    }
    
    session = requests.Session()
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'http://220.156.188.226/CREBS/',
        'Origin': 'http://220.156.188.226'
    }
    session.headers.update(headers)

    print(f"   [Attempt {attempt_num}] Trying proxy: {proxy_url} ...")

    try:
        # 1. GET Login Page (Test connection)
        r_get = session.get(LOGIN_URL, proxies=proxies, timeout=15)
        if r_get.status_code != 200:
            return False, "Page load failed"

        # 2. POST Login
        payload = {'txtEmail': EMAIL, 'txtPassword': PASSWORD, 'returnUrl': ''}
        r_post = session.post(LOGIN_URL, data=payload, proxies=proxies, timeout=15)

        # 3. Validate
        if "Signout" in r_post.text or "Welcome" in r_post.text:
            return True, r_post.text # Success! Return HTML
        else:
            return False, "Login failed (Bad credentials or blocking)"

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
            icon = "✅" if "pass" in res['status'].lower() else "❌" if "fail" in res['status'].lower() else "📝"
            message += f"{icon} <b>{res['paper']}</b>\nType: {res['type']}\nDate: {res['date']}\nStatus: <b>{res['status']}</b>\n\n"
            has_update = True
        
        if has_update:
            send_telegram(message)
            print("✅ Telegram sent.")
    else:
        print("🤷 Login worked, but no results found in table.")

def run():
    print("--- Starting Auto-Proxy Scraper ---")
    
    # 1. Get List
    proxy_list = get_indian_proxies()
    if not proxy_list:
        print("❌ No proxies available. Exiting.")
        sys.exit(1)

    # 2. Shuffle to randomize
    random.shuffle(proxy_list)

    # 3. Try up to 10 proxies before giving up
    max_attempts = 15
    success = False

    for i, proxy in enumerate(proxy_list[:max_attempts]):
        is_success, result_data = attempt_scrape_with_proxy(proxy, i+1)
        
        if is_success:
            print("🎉 SUCCESS! Connection established.")
            parse_and_notify(result_data)
            success = True
            break
        else:
            print(f"   ❌ Failed: {result_data}")

    if not success:
        print("❌ All proxy attempts failed. The site might be down or all proxies are bad.")
        send_telegram("⚠️ <b>CREBS Scraper Failed:</b>\nTried 15 Indian proxies, but all failed to connect.")
        sys.exit(1)

if __name__ == "__main__":
    run()
