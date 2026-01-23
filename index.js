const puppeteer = require('puppeteer');
const axios = require('axios');

// Configuration from GitHub Secrets
const EMAIL = process.env.USER_EMAIL;
const PASSWORD = process.env.USER_PASSWORD;
const TELEGRAM_TOKEN = process.env.TELEGRAM_TOKEN;
const TELEGRAM_CHAT_ID = process.env.TELEGRAM_CHAT_ID;

const LOGIN_URL = 'http://220.156.188.226/CREBS/';

async function run() {
  console.log('Starting Result Checker...');
  
  // Launch options to bypass "Blocked by Client" errors
  const browser = await puppeteer.launch({
    headless: true, // "true" is the new standard for latest Puppeteer
    ignoreHTTPSErrors: true,
    args: [
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--disable-web-security',
      '--disable-features=IsolateOrigins,site-per-process,SafeBrowsing', // <--- Key fix for IP blocking
      '--allow-running-insecure-content',
      '--disable-blink-features=AutomationControlled',
      '--disable-extensions',
      '--window-size=1920,1080'
    ]
  });
  
  const page = await browser.newPage();

  // 1. Spoof a real User Agent (looks like Windows 10 Chrome)
  await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36');
  
  // 2. Bypass Content Security Policy
  await page.setBypassCSP(true);

  try {
    console.log('Navigating to login page...');
    // Extended timeout to 2 minutes for slow ASP.NET servers
    await page.goto(LOGIN_URL, { waitUntil: 'networkidle2', timeout: 120000 });

    console.log('Filling credentials...');
    // Type credentials (using the IDs from your HTML)
    await page.type('#txtEmail', EMAIL);
    await page.type('#txtPassword', PASSWORD);

    // Click login and wait for the page to actually change
    await Promise.all([
      page.waitForNavigation({ waitUntil: 'networkidle2', timeout: 120000 }),
      page.click('input[type="image"][title="Login"]'), 
    ]);

    console.log('Login successful. Scanning for results...');

    // 3. Scrape the Table
    const results = await page.evaluate(() => {
      const data = [];
      const rows = document.querySelectorAll('tr');

      rows.forEach(row => {
        // Look for cells with the specific class from your HTML
        const cells = row.querySelectorAll('td.tablebodytext');
        // Your target rows have exactly 4 columns
        if (cells.length === 4) {
          data.push({
            paper: cells[0].innerText.trim(),
            type: cells[1].innerText.trim(),
            date: cells[2].innerText.trim(),
            status: cells[3].innerText.trim()
          });
        }
      });
      return data;
    });

    // 4. Process Results and Send Notification
    if (results.length > 0) {
      console.log(`Found ${results.length} result rows.`);
      let message = `📢 <b>CREBS Result Update</b>\n\n`;
      let hasUpdate = false;

      results.forEach(r => {
        let icon = '📝';
        if(r.status.toLowerCase().includes('pass')) icon = '✅';
        if(r.status.toLowerCase().includes('fail')) icon = '❌';
        
        message += `${icon} <b>${r.paper}</b>\n`;
        message += `Type: ${r.type}\n`;
        message += `Date: ${r.date}\n`;
        message += `Status: <b>${r.status}</b>\n\n`;
        
        hasUpdate = true;
      });

      // Send to Telegram if we found data
      if (hasUpdate) {
        await sendTelegram(message);
      }
    } else {
      console.log('No results found in the table.');
    }

  } catch (error) {
    console.error('Error occurred:', error);
    // Ignore timeout errors for Telegram alerts to avoid spam
    if (!error.message.includes('Timeout')) {
       await sendTelegram(`⚠️ <b>Error checking CREBS results:</b>\n${error.message}`);
    }
    process.exit(1);
  } finally {
    await browser.close();
  }
}

async function sendTelegram(text) {
  const url = `https://api.telegram.org/bot${TELEGRAM_TOKEN}/sendMessage`;
  try {
    await axios.post(url, {
      chat_id: TELEGRAM_CHAT_ID,
      text: text,
      parse_mode: 'HTML'
    });
    console.log('Telegram notification sent.');
  } catch (err) {
    console.error('Failed to send Telegram message', err);
  }
}

// Run the main function
run();
