#!/usr/bin/env python3
"""
Daily AI News Substack Bot
Runs every morning at 10am via macOS launchd.
- Scrapes top AI/LLM/Agent news from the last 24 hours
- Writes a Substack post (title, subtitle, body, cover image)
- Publishes a DRAFT to dronagangarapu.substack.com via Substack API
"""

import os
import json
import time
import datetime
import requests
from dotenv import load_dotenv

# ── Load credentials ─────────────────────────────────────────────────────────
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
SUBSTACK_COOKIE    = os.getenv("SUBSTACK_COOKIE")          # substack.sid=... from browser
SUBSTACK_PUB       = "drona23.substack.com"
PEXELS_API_KEY     = os.getenv("PEXELS_API_KEY", "")       # optional – for cover image

# ── 1. Fetch AI news via free Google News RSS feeds ──────────────────────────
import xml.etree.ElementTree as ET
from urllib.parse import quote

RSS_QUERIES = [
    "artificial intelligence",
    "large language model LLM",
    "AI agents",
    "OpenAI OR Anthropic OR Gemini",
    "generative AI",
]

def fetch_news_via_rss(queries: list[str], max_per_feed: int = 5) -> str:
    """Fetch headlines + real article URLs from Google News RSS."""
    articles = []
    seen = set()

    for q in queries:
        url = f"https://news.google.com/rss/search?q={quote(q)}+when:1d&hl=en-US&gl=US&ceid=US:en"
        try:
            resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            root = ET.fromstring(resp.content)
            items = root.findall(".//item")[:max_per_feed]
            for item in items:
                title    = item.findtext("title", "").strip()
                desc     = item.findtext("description", "").strip()
                source   = item.findtext("source", "Unknown")
                link     = item.findtext("link", "").strip()
                if title and title not in seen:
                    seen.add(title)
                    # Follow the Google News redirect to get the real article URL
                    real_url = link
                    try:
                        r = requests.get(link, timeout=8, allow_redirects=True,
                                         headers={"User-Agent": "Mozilla/5.0"})
                        real_url = r.url
                    except Exception:
                        pass
                    articles.append(
                        f"• [{source}] {title}\n"
                        f"  URL: {real_url}\n"
                        f"  {desc[:200]}"
                    )
        except Exception as e:
            print(f"[WARN] RSS fetch failed for '{q}': {e}")

    if not articles:
        return ""
    return "\n\n".join(articles)


# ── 2. Generate the Substack post with Claude ────────────────────────────────
def generate_post(news_context: str) -> dict:
    """Ask Claude to write the full Substack post."""
    import anthropic
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    today = datetime.datetime.now().strftime("%B %d, %Y")

    prompt = f"""You are a skilled tech journalist writing a daily Substack newsletter called "AI Daily Digest" for drona23.substack.com.

Today is {today}. Here are the top AI news items from the last 24 hours. Each item includes the source, headline, a real article URL, and a short description:

{news_context}

STRICT RULES — you must follow these without exception:
1. ONLY write about stories that appear in the news list above. Do NOT invent, guess, or hallucinate any story, company, product, or event that is not explicitly mentioned above.
2. Every claim in the post must be traceable to one of the news items above.
3. For References, copy the exact URLs provided in the "URL:" field of the news items above. Do NOT make up or shorten URLs.

Write a Substack newsletter post following ALL of these requirements. Return your answer as a JSON object with these exact keys:

- "title": A catchy, SEO-optimised title (max 10 words). Make it punchy and curiosity-driven.

- "subtitle": A one-sentence subtitle that clearly covers what happened in AI in the last 24 hours (max 20 words). Should feel timely and newsy.

- "body": The full post body in Markdown. Must include ALL of the following sections in order:

  1. **Intro** (2-3 sentences): Hook the reader with the most exciting AI development today. Human, conversational tone — like texting a smart friend.

  2. **Today's Top AI Stories** (3-4 sections): Each section must have:
     - A bold headline with the story name
     - 2-3 sentences summarising what happened and why it matters
     - A "How YOU can use this today" subsection with three short lines. Each line must start with ONLY the label and a colon — no dash, no bullet, no asterisk before the label. Format exactly like this:
       Students: [one sentence example]
       Professionals: [one sentence example]
       Everyday People: [one sentence example]

  3. **New AI Tool Spotlight** (if any new tool was released in the last 24h): Give a brief, honest review — what it does, who it's for, pros/cons, and a link if available.

  4. **Key Takeaways**: Write exactly 3 short takeaway sentences, each on its own line, each starting with "- " (a single dash and space). Do NOT use "- " on any subsequent lines in the same list — only the very first item should start with "- ", the remaining two items should have NO dash or bullet prefix at all, just plain text on a new line.

  5. **References**: Do NOT include references inside the body text. They will be handled separately.

  6. **Disclaimer**: End with this exact text:
     "Disclaimer: This newsletter is for informational purposes only. AI tools and capabilities change rapidly — always verify information before making decisions based on it."

  - CRITICAL: Do NOT use any emojis anywhere in the post. No emojis in headings, bullet points, or body text — write in plain text only.
  - Use natural, human-like writing with popular SEO keywords (e.g. "AI tools 2026", "how to use AI", "AI for students", "AI productivity", "best AI apps")
  - Target length: 400–600 words (2-minute read)
  - No jargon, no PhD-speak — write for a general audience

- "references": A JSON array of objects, each with "name" and "url". Use the exact URLs from the "URL:" fields in the news items above. Example format: [{{"name": "TechCrunch", "url": "https://techcrunch.com/..."}}, {{"name": "WIRED", "url": "https://wired.com/..."}}]. Only include URLs that were explicitly given to you — never make up a URL.

- "cover_image_query": A vivid, specific 5-7 word phrase describing a title picture for this post (e.g. "student using AI laptop glowing futuristic")

- "cover_image_description": A 1-2 sentence description of what the ideal cover image for this post should look like (for the reader's reference).

Return ONLY the JSON object, no extra text."""

    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=8096,
        messages=[{"role": "user", "content": prompt}]
    )

    raw = response.content[0].text.strip()
    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())


# ── 3. Fetch and save a cover image from Pexels (free) ───────────────────────
def fetch_cover_image(query: str, post_title: str) -> str | None:
    """Fetch a royalty-free cover image from Pexels and save it locally.
    Returns the local file path, or None on failure."""
    if not PEXELS_API_KEY:
        print("[INFO] No PEXELS_API_KEY set – skipping cover image.")
        return None
    try:
        resp = requests.get(
            "https://api.pexels.com/v1/search",
            headers={"Authorization": PEXELS_API_KEY},
            params={"query": query, "per_page": 1, "orientation": "landscape"},
            timeout=10
        )
        data = resp.json()
        if not data.get("photos"):
            print("[WARN] No Pexels photos found for query.")
            return None

        image_url = data["photos"][0]["src"]["large2x"]

        # Save image locally in SubstackBot/images/ using the post title as filename
        images_dir = os.path.join(os.path.dirname(__file__), "images")
        os.makedirs(images_dir, exist_ok=True)

        # Sanitise title for use as a filename
        safe_title = "".join(c if c.isalnum() or c in " -_" else "_" for c in post_title)
        safe_title = safe_title.strip().replace(" ", "_")[:80]
        today_str  = datetime.datetime.now().strftime("%Y-%m-%d")
        filename   = f"{today_str}_{safe_title}.jpg"
        local_path = os.path.join(images_dir, filename)

        img_resp = requests.get(image_url, timeout=20)
        with open(local_path, "wb") as f:
            f.write(img_resp.content)

        print(f"[OK] Cover image saved to {local_path}")
        return local_path

    except Exception as e:
        print(f"[WARN] Pexels image fetch/save failed: {e}")
    return None


# ── 4. Post draft to Substack via Playwright browser automation ───────────────
def post_to_substack_draft(post: dict, cover_image_url: str | None) -> dict:
    """
    Opens a real Chromium browser, injects your session cookies,
    navigates to the Substack editor, and fills in the post using
    simple click-and-type (no JavaScript DOM manipulation).
    """
    if not SUBSTACK_COOKIE:
        raise ValueError("SUBSTACK_COOKIE not set in .env")

    from playwright.sync_api import sync_playwright
    import time as _time

    # Parse cookie string into list of dicts for Playwright
    cookies = []
    for part in SUBSTACK_COOKIE.split(";"):
        part = part.strip()
        if "=" in part:
            name, value = part.split("=", 1)
            name = name.strip()
            value = value.strip()
            for domain in [".substack.com", "substack.com", f".{SUBSTACK_PUB}", SUBSTACK_PUB]:
                cookies.append({
                    "name": name,
                    "value": value,
                    "domain": domain,
                    "path": "/",
                })

    with sync_playwright() as p:
        print("  → Launching browser…")
        browser = p.chromium.launch(
            headless=False,
            args=["--start-maximized"]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
            java_script_enabled=True,
            extra_http_headers={"Accept-Language": "en-US,en;q=0.9"}
        )
        context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        context.add_cookies(cookies)
        page = context.new_page()

        print("  → Navigating to Substack home…")
        page.goto("https://substack.com", wait_until="domcontentloaded", timeout=60000)
        _time.sleep(3)
        print(f"  → Current URL: {page.url}")

        if "login" in page.url or "signin" in page.url:
            browser.close()
            raise Exception("Not logged in — cookies may have expired. Please refresh them.")

        # Click Create → Article
        print("  → Clicking Create button…")
        page.click('button:has-text("Create")', timeout=10000)
        _time.sleep(2)

        print("  → Clicking Article from dropdown…")
        page.click(
            'a:has-text("Article"), button:has-text("Article"), '
            'li:has-text("Article"), span:has-text("Article")',
            timeout=8000
        )

        # Wait for the editor URL to appear
        print("  → Waiting for editor to load…")
        page.wait_for_url("**/publish/post*", timeout=30000)
        page.wait_for_load_state("domcontentloaded")
        _time.sleep(5)
        print(f"  → Editor URL: {page.url}")

        # Only reload on a genuine error page (match title, not page body content)
        page_title = page.title()
        print(f"  → Page title: {page_title}")
        if page_title in ("Error - Substack", "404 - Substack", "Substack"):
            print("  → Error page detected, reloading…")
            page.reload(wait_until="domcontentloaded")
            _time.sleep(10)
            print(f"  → After reload: {page.url} — title: {page.title()}")

        # Extra wait for the editor JS to fully initialise
        _time.sleep(5)

        screenshot_path = os.path.join(os.path.dirname(__file__), "debug_screenshot.png")
        page.screenshot(path=screenshot_path)
        print(f"  → Screenshot saved: {screenshot_path}")

        # Wait for the editor to be ready — any data-placeholder element or ProseMirror
        print("  → Waiting for editor to be ready…")
        try:
            page.wait_for_selector('[data-placeholder], .ProseMirror', timeout=30000)
            print("  → Editor ready")
        except Exception as wait_err:
            print(f"  [WARN] Editor selector timed out ({wait_err}) — taking screenshot and continuing anyway")
            page.screenshot(path=os.path.join(os.path.dirname(__file__), "editor_timeout.png"))
        _time.sleep(3)

        # ── Fill BODY (title + subtitle + body all in one field) ─────────────────
        # Substack's Title/Subtitle fields have no data-placeholder and can't be
        # targeted reliably. Instead, we write title and subtitle as the opening
        # lines of the body — bold title, plain subtitle, then a divider, then
        # the main post content.
        full_body = (
            f"**{post['title']}**\n\n"
            f"{post['subtitle']}\n\n"
            f"---\n\n"
            f"{post['body']}"
        )

        print("  → Clicking body field…")
        body_loc = None
        for sel in [
            '.ProseMirror[contenteditable="true"]',
            'div.ProseMirror',
            '[data-placeholder*="writing"]',
            '[contenteditable="true"]',
        ]:
            try:
                loc = page.locator(sel).first
                loc.wait_for(state="visible", timeout=8000)
                loc.click()
                _time.sleep(0.5)
                body_loc = sel
                break
            except Exception as e:
                print(f"  [WARN] Body click – {sel}: {e}")
        if not body_loc:
            print("  [ERROR] Could not click body field")

        # ── Type the full body content ────────────────────────────────────────
        print("  → Typing title + subtitle + body…")
        try:
            page.keyboard.type(full_body, delay=10)
            print("  → Body typed")
        except Exception as e:
            print(f"  [ERROR] Could not type body: {e}")
        _time.sleep(2)

        # ── Type References as real clickable hyperlinks using Cmd+K ─────────
        references = post.get("references", [])
        if references:
            print("  → Adding references as hyperlinks…")
            page.keyboard.type("\n\nReferences\n", delay=10)
            _time.sleep(0.3)
            for ref in references:
                name = ref.get("name", "Source")
                url  = ref.get("url", "")
                if not url:
                    continue
                try:
                    # Type the source name
                    page.keyboard.type(name, delay=20)
                    # Select the typed name using Shift+ArrowLeft
                    for _ in range(len(name)):
                        page.keyboard.press("Shift+ArrowLeft")
                    _time.sleep(0.2)
                    # Open Substack's link dialog with Cmd+K
                    page.keyboard.press("Meta+k")
                    _time.sleep(1)
                    # Type the URL and confirm
                    page.keyboard.type(url, delay=10)
                    page.keyboard.press("Enter")
                    _time.sleep(0.5)
                    # Move cursor to end of link and go to next line
                    page.keyboard.press("ArrowRight")
                    page.keyboard.press("Enter")
                    print(f"  → Hyperlink added: {name}")
                except Exception as e:
                    print(f"  [WARN] Hyperlink for {name}: {e}")
            _time.sleep(1)
        _time.sleep(2)

        # Wait for Substack auto-save
        print("  → Waiting for auto-save (10s)…")
        _time.sleep(10)

        page.screenshot(path=os.path.join(os.path.dirname(__file__), "pre_buttons_screenshot.png"))

        # ── Insert Subscribe button via toolbar "Button" dropdown ─────────────
        # The "Button" item in the editor toolbar inserts CTA buttons into the post.
        # Click it once → pick "Subscribe", then click it again → pick "Share post".
        print("  → Clicking toolbar 'Button' → Subscribe…")
        try:
            # First move cursor to end of body so the button is inserted there
            page.keyboard.press("End")
            _time.sleep(0.3)

            # Click the "Button" toolbar item
            toolbar_btn = page.locator('button:has-text("Button")').first
            toolbar_btn.wait_for(state="visible", timeout=8000)
            toolbar_btn.click()
            _time.sleep(1)

            # Pick "Subscribe" from the dropdown
            page.locator('li:has-text("Subscribe"), [role="menuitem"]:has-text("Subscribe"), button:has-text("Subscribe")').first.click()
            print("  → 'Subscribe' button inserted into post")
            _time.sleep(1)
        except Exception as e:
            print(f"  [WARN] Subscribe button insert failed: {e}")

        # ── Insert Share Post button via toolbar "Button" dropdown ────────────
        print("  → Clicking toolbar 'Button' → Share post…")
        try:
            # Click the "Button" toolbar item again
            toolbar_btn = page.locator('button:has-text("Button")').first
            toolbar_btn.wait_for(state="visible", timeout=8000)
            toolbar_btn.click()
            _time.sleep(1)

            # Pick "Share post" from the dropdown
            page.locator('li:has-text("Share post"), [role="menuitem"]:has-text("Share post")').first.click()
            print("  → 'Share post' button inserted into post")
            _time.sleep(1)
        except Exception as e:
            print(f"  [WARN] Share post button insert failed: {e}")

        # Final auto-save after inserting the CTA buttons
        print("  → Waiting for final auto-save (8s)…")
        _time.sleep(8)

        _time.sleep(5)
        final_url = page.url
        page.screenshot(path=os.path.join(os.path.dirname(__file__), "final_screenshot.png"))
        print(f"  → Done. Final URL: {final_url}")
        browser.close()

    return {"draft_title": post["title"], "url": final_url}


# ── 5. Save a local backup of the post ───────────────────────────────────────
def save_local_backup(post: dict):
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    backup_dir = os.path.join(os.path.dirname(__file__), "posts")
    os.makedirs(backup_dir, exist_ok=True)
    path = os.path.join(backup_dir, f"{today}_ai_digest.md")
    with open(path, "w") as f:
        f.write(f"# {post['title']}\n")
        f.write(f"**{post['subtitle']}**\n\n")
        if post.get("cover_image_description"):
            f.write(f"*Cover image: {post['cover_image_description']}*\n\n")
        f.write(post["body"])
    print(f"[OK] Local backup saved to {path}")


# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    print(f"\n{'='*60}")
    print(f"  AI Daily Substack Bot – {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*60}\n")

    print("[1/4] Fetching today's AI news from Google News RSS…")
    news_context = fetch_news_via_rss(RSS_QUERIES)
    if not news_context.strip():
        print("[WARN] News context is empty – aborting.")
        return

    print("[2/4] Generating Substack post with Claude…")
    post = generate_post(news_context)
    print(f"  Title   : {post['title']}")
    print(f"  Subtitle: {post['subtitle']}")

    print("[3/4] Fetching and saving cover image…")
    cover_local_path = fetch_cover_image(
        post.get("cover_image_query", "artificial intelligence technology"),
        post["title"]
    )
    if post.get("cover_image_description"):
        print(f"  Cover image desc: {post['cover_image_description']}")

    print("[4/4] Posting draft to Substack…")
    try:
        result = post_to_substack_draft(post, cover_local_path)
        draft_id = result.get("id", "unknown")
        print(f"\n✅ Success! Draft ready at:")
        print(f"   https://{SUBSTACK_PUB}/publish/post/{draft_id}")
    except Exception as e:
        print(f"[ERROR] Could not post to Substack: {e}")
        print("  Saving post locally as fallback…")

    save_local_backup(post)
    print("\nDone!")


if __name__ == "__main__":
    main()
