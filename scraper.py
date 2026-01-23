import os
import requests
from bs4 import BeautifulSoup
import sys

# Configuration
EMAIL = os.environ.get('USER_EMAIL')
PASSWORD = os.environ.get('USER_PASSWORD')
BOT_TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

LOGIN_URL = "http://220.156.188.226/CREBS/"
# The page usually redirects to this after login, but we'll capture it via session
HOME_URL = "http://220.156.188.226/CREBS/" 

def send_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        requests.post(url, json=payload)
        print("Telegram sent.")
    except Exception as e:
        print(f"Failed to send Telegram: {e}")

def run():
    print("Starting Python Scraper...")
    
    # 1. Setup Session (Keeps cookies/login active)
    session = requests.Session()
    
    # Fake a real browser to avoid getting blocked by the server
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Origin': 'http://220.156.188.226',
        'Referer': 'http://220.156.188.226/CREBS/'
    }
    session.headers.update(headers)

    try:
        # 2. Get the Login Page first (to establish session cookies)
        print("Fetching login page...")
        r_get = session.get(LOGIN_URL, timeout=30)
        
        # 3. Perform Login
        print("Logging in...")
        payload = {
            'txtEmail': EMAIL,
            'txtPassword': PASSWORD,
            'returnUrl': '' 
            # Note: Sometimes ASP.NET needs hidden fields like __VIEWSTATE. 
            # Based on your URL structure (MVC), usually just user/pass is enough.
        }
        
        # We post to the same URL as the login page based on your HTML
        r_post = session.post(LOGIN_URL, data=payload, allow_redirects=True)
        
        if r_post.status_code != 200:
            print(f"Login failed with status code: {r_post.status_code}")
            sys.exit(1)

        # 4. Check if login worked
        # We look for the "Signout" link which only appears if logged in
        if "Signout" not in r_post.text and "Welcome" not in r_post.text:
            print("Login failed. 'Signout' or 'Welcome' not found in response.")
            # Optional: print specific error from page if needed
            # soup_err = BeautifulSoup(r_post.text, 'lxml')
            # print(soup_err.find(id="error_message").text)
            sys.exit(1)

        print("Login successful! Parsing results...")

        # 5. Parse the HTML
        soup = BeautifulSoup(r_post.text, 'lxml')
        
        # Find all rows with result data
        # Your HTML uses 'tablebodytext' class for data cells
        data_cells = soup.find_all('td', class_='tablebodytext')
        
        # The table has 4 columns per row. We group cells by 4.
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

        # 6. Process and Notify
        if results:
            print(f"Found {len(results)} results.")
            message = "📢 <b>CREBS Result Update</b>\n\n"
            has_update = False
            
            for res in results:
                icon = "📝"
                if "pass" in res['status'].lower(): icon = "✅"
                elif "fail" in res['status'].lower(): icon = "❌"
                
                message += f"{icon} <b>{res['paper']}</b>\n"
                message += f"Type: {res['type']}\n"
                message += f"Date: {res['date']}\n"
                message += f"Status: <b>{res['status']}</b>\n\n"
                has_update = True
            
            if has_update:
                send_telegram(message)
        else:
            print("No results found in the table.")

    except Exception as e:
        print(f"Error occurred: {e}")
        send_telegram(f"⚠️ <b>Error in Scraper:</b>\n{str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    run()
