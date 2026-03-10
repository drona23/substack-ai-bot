# SubstackBot – Setup Guide

This bot runs every morning at **10:00 AM**, scrapes the latest AI news, writes a full Substack post using Claude, and saves a draft to **dronagangarapu.substack.com** automatically.

---

## Step 1 – Install Python dependencies

Open Terminal and run:

```bash
pip3 install anthropic requests python-dotenv markdown
```

---

## Step 2 – Set up your credentials

```bash
cd ~/SubstackBot
cp .env.template .env
open .env   # edit with any text editor
```

Fill in the three values:

### A. Anthropic API Key
- Go to [console.anthropic.com](https://console.anthropic.com)
- Create an API key and paste it as `ANTHROPIC_API_KEY`

### B. Substack Session Cookie
This lets the bot post on your behalf without needing a password.

1. Open Chrome and go to [dronagangarapu.substack.com](https://dronagangarapu.substack.com)
2. Make sure you're **logged in**
3. Press `Cmd + Option + I` to open DevTools
4. Go to **Application → Cookies → https://dronagangarapu.substack.com**
5. Find the cookie named `connect.sid`
6. Copy its full value (starts with `s%3A...`)
7. In `.env`, set: `SUBSTACK_COOKIE=connect.sid=s%3A...`

> ⚠️ This cookie expires periodically. If the bot stops posting, repeat this step.

### C. Pexels API Key (optional, for cover images)
- Sign up free at [pexels.com/api](https://www.pexels.com/api/)
- Paste your key as `PEXELS_API_KEY`

---

## Step 3 – Test it manually

```bash
python3 ~/SubstackBot/daily_ai_post.py
```

Check your Substack dashboard for a new draft. Posts are saved as drafts — **you review and publish them yourself.**

Local backups of every post are saved in `~/SubstackBot/posts/`.

---

## Step 4 – Schedule it to run at 10 AM every day

```bash
cp ~/SubstackBot/com.drona.daily-ai-post.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.drona.daily-ai-post.plist
```

To verify it's scheduled:
```bash
launchctl list | grep drona
```

To check logs after it runs:
```bash
cat /tmp/daily_ai_post.log
cat /tmp/daily_ai_post_err.log
```

---

## To stop / uninstall

```bash
launchctl unload ~/Library/LaunchAgents/com.drona.daily-ai-post.plist
rm ~/Library/LaunchAgents/com.drona.daily-ai-post.plist
```

---

## What the bot does each morning

1. 🔍 Searches the web for AI, LLM, AI agents, and GenAI news from the last 24 hours
2. ✍️ Uses Claude to write a polished newsletter with a title, subtitle, and full body
3. 🖼️ Fetches a relevant cover image from Pexels
4. 📬 Creates a **draft** on your Substack (you review before publishing)
5. 💾 Saves a local Markdown backup in `~/SubstackBot/posts/`
