🎓 CREBS Result Notifier & Scraper
This is an automated tool designed to check the CREBS (Comprehensive Result Evaluation & Booking System) portal for new exam results. It logs into the student dashboard, scrapes the latest result status, and sends an instant notification to your Telegram account.

Because the CREBS portal is geo-restricted (accessible only from India) and often slow, this tool includes built-in strategies to bypass blocks and handle server timeouts.

✨ Features
🚀 Automated Login: Handles ASP.NET session management and authentication automatically.

📱 Telegram Alerts: Sends a formatted message with Pass/Fail status (✅, ❌) directly to your phone.

🌍 Geo-Block Bypass:

Auto-Proxy Mode: Automatically fetches and rotates Indian proxies to connect from GitHub Cloud.

Self-Hosted Mode: Runs on your local machine (India IP) for 100% reliability.

⏰ Scheduled Checks: Runs automatically every 3 hours via GitHub Actions.

🔒 Secure: Credentials are stored in GitHub Secrets, never hardcoded in the script.

🛠️ Prerequisites
Before setting this up, you need:

A Telegram Bot:

Chat with @BotFather to create a bot and get the API Token.

Chat with @userinfobot to get your personal Chat ID.

CREBS Credentials: Your valid Email and Password for the portal.
