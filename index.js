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
  
  // "Nuclear" launch options to disable ALL security & phishing checks
  const browser = await puppeteer.launch({
    headless: true,
    ignoreHTTPSErrors: true,
    args: [
      '--no-sandbox',
      '--disable-setuid-sandbox',
      
      // Security & Phishing Bypasses
      '--disable-web-security',
      '--disable-features=IsolateOrigins,site-per-process,SafeBrowsing', 
      '--disable-site-isolation-trials',
      '--disable-client-side-phishing-detection',
      '--disable-component-update', // Prevents downloading new blocklists
      '--safebrowsing-disable-auto-update', 
      
      // Content & Certificate Bypasses
      '--allow-running-insecure-content',
      '--ignore-certificate-errors',
      
      // Bot Hiding
      '--disable-blink-features=AutomationControlled',
      '--disable-extensions',
      '--disable-infobars',
      '--window-size=1920,1080'
    ]
  });
  
  const page = await browser.newPage();

  // 1. Spoof User Agent
  await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36');
  
  // 2. Bypass CSP & standard headers
  await page.setBypassCSP(true);

  try {
    console.log('Navigating to login page...');
    
    // Using 'domcontentloaded' is faster and less strict than networkidle2
    // We increase timeout to 2 minutes for slow government servers
    await page.goto(LOGIN_URL, { waitUntil: 'domcontentloaded', timeout: 120000 });

    console.log('Filling credentials...');
    
    // Wait for the email field to actually exist before typing
    await page.waitForSelector('#txtEmail', { timeout: 60000 });
    
    await page.type('#txtEmail', EMAIL);
    await page.type('#txtPassword', PASSWORD);

    // Click login and wait for navigation
    await Promise.all([
      page.waitForNavigation({ waitUntil: 'domcontentloaded', timeout: 120000 }),
      page.click('input[type="image"][title="Login"]'), 
    ]);

    console.log('Login successful. Scanning for results...');

    // 3. Scrape the Table
    // We wait for the table row to appear to ensure the result page loaded
    try {
        await page.waitForSelector('td.tablebodytext', { timeout: 30000 });
    } catch (e) {
        console.log("No table rows found immediately, checking page content...");
    }

    const results = await page.evaluate(() => {
      const data = [];
      const rows = document.querySelectorAll('tr');

      rows.forEach(row => {
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

    // 4. Process Results
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

      if (hasUpdate) {
        await sendTelegram(message);
      }
    } else {
      console.log('No results found in the table. (This might be normal if no exams are listed)');
    }

  } catch (error) {
    console.error('Error occurred:', error);
    // Filter out timeout errors to avoid spam
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

run();
