# AI Daily Substack Bot

An end-to-end automation that runs every morning at 7 AM, scrapes the latest AI news, writes a full newsletter post using Claude, and publishes a draft to Substack that completely on its own.

Built by **Drona Gangarapu** - MS Data Science, Pace University
Built using **Claude Cowork** by Anthropic

---

## What it does

1. Scrapes real-time AI news from Google News RSS (no API cost)
2. Sends the news to Anthropic's Claude API to write a structured newsletter post
3. Fetches a relevant cover image from Pexels and saves it locally
4. Opens a real browser using Playwright, logs into Substack via session cookies
5. Types the full post into the Substack editor
6. Inserts Subscribe and Share Post CTA buttons
7. Saves the draft ready for one-click publish
8. Runs automatically every day at 7 AM via macOS launchd

---

## Tech Stack

| Tool | Purpose |
|---|---|
| Python | Core automation logic |
| Anthropic Claude API | AI-powered post writing |
| Playwright | Browser automation |
| Google News RSS | Free real-time news scraping |
| Pexels API | Royalty-free cover images |
| macOS launchd | Daily 7 AM scheduling |

---

## Setup

### 1. Install dependencies
```bash
pip install anthropic requests python-dotenv playwright
playwright install chromium
```

### 2. Create your `.env` file
```bash
cp .env.template .env
```
Then fill in your credentials:
```
ANTHROPIC_API_KEY=your_key_here
SUBSTACK_COOKIE=your_full_cookie_string_here
PEXELS_API_KEY=your_key_here
```

**How to get your Substack cookie:**
- Log into your Substack in Chrome
- Open DevTools → Application → Cookies → substack.com
- Copy the full cookie string from your request headers

### 3. Test it manually
```bash
python3 ~/SubstackBot/daily_ai_post.py
```

### 4. Schedule it at 7 AM daily
```bash
cp com.drona.daily-ai-post.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.drona.daily-ai-post.plist
```

### 5. Check logs after it runs
```bash
cat /tmp/daily_ai_post.log
cat /tmp/daily_ai_post_err.log
```

---

## Project Structure

```
SubstackBot/
├── daily_ai_post.py              # Main automation script
├── com.drona.daily-ai-post.plist # macOS launchd schedule config
├── .env.template                 # Credentials template (copy to .env)
├── .gitignore
├── README.md
├── images/                       # Cover images saved here (gitignored)
└── posts/                        # Local post backups (gitignored)
```

---

## How the post is structured

Each generated post includes:
- Bold title + subtitle at the top
- Intro hook
- 3–4 top AI stories with "How YOU can use this today" breakdowns for Students, Professionals, and Everyday People
- New AI Tool Spotlight
- Key Takeaways
- References with exact source URLs (no hallucinations, every story is grounded in the RSS feed)
- Subscribe + Share Post buttons
- Disclaimer

---

## Notes

- Your Mac must be **on and connected to the internet** at 7 AM for the schedule to trigger
- If the Mac is asleep, launchd will run the job when it next wakes up
- The `.env` file is gitignored — never commit your API keys
