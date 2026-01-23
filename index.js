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
  
const browser = await puppeteer.launch({
    headless: true, // Use modern headless mode
    ignoreHTTPSErrors: true, // Ignore SSL/security certificate issues
    args: [
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--disable-web-security', // Disable standard security checks
      '--disable-features=IsolateOrigins,site-per-process', // prevent site isolation
      '--allow-running-insecure-content', // Allow HTTP content
      '--disable-blink-features=AutomationControlled', // Try to hide that we are a bot
      '--disable-extensions' 
    ]
  });
  
  const page = await browser.newPage();

  try {
    // 1. Navigate to Login
    console.log('Navigating to login page...');
    await page.goto(LOGIN_URL, { waitUntil: 'networkidle2', timeout: 60000 });

    // 2. Fill Credentials based on your HTML ids
    console.log('Filling credentials...');
    await page.type('#txtEmail', EMAIL);
    await page.type('#txtPassword', PASSWORD);

    // 3. Click Login and Wait for Navigation
    // The login button is an image input in the provided HTML
    await Promise.all([
      page.waitForNavigation({ waitUntil: 'networkidle2' }),
      page.click('input[type="image"][title="Login"]'), 
    ]);

    console.log('Login successful. Scanning for results...');

    // 4. Scrape the Table
    // We look for rows that contain result data. 
    // Based on your HTML, the headers use class "listViewTable_Header" 
    // and data uses class "tablebodytext".
    const results = await page.evaluate(() => {
      const data = [];
      // Select all rows in the table structure
      const rows = document.querySelectorAll('tr');

      rows.forEach(row => {
        const cells = row.querySelectorAll('td.tablebodytext');
        // We need rows that have exactly 4 cells (Paper, Type, Date, Status)
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

    // 5. Process Results
    if (results.length > 0) {
      console.log(`Found ${results.length} result rows.`);
      let message = `📢 <b>CREBS Result Update</b>\n\n`;
      let hasUpdate = false;

      results.forEach(r => {
        // Format the message
        let icon = '📝';
        if(r.status.toLowerCase().includes('pass')) icon = '✅';
        if(r.status.toLowerCase().includes('fail')) icon = '❌';
        
        message += `${icon} <b>${r.paper}</b>\n`;
        message += `Type: ${r.type}\n`;
        message += `Date: ${r.date}\n`;
        message += `Status: <b>${r.status}</b>\n\n`;
        
        hasUpdate = true;
      });

      // Send to Telegram
      if (hasUpdate) {
        await sendTelegram(message);
      }
    } else {
      console.log('No results found in the table.');
    }

  } catch (error) {
    console.error('Error occurred:', error);
    await sendTelegram(`⚠️ <b>Error checking CREBS results:</b>\n${error.message}`);
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
