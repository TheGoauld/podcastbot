# PodcastBot

AI-powered podcast generator. Drop article links into a Matrix chat room, type `podcast`, and get a two-host conversational podcast episode with an RSS feed you can subscribe to in any podcast app.

**Pipeline:** Article URLs → LLM summarization → Deep research → Two-host script → OpenAI TTS → MP3 episode → RSS feed

## What You Need

| Component | Cost | Purpose |
|-----------|------|---------|
| **Ollama** (local LLM) | Free | Summarizes articles, writes podcast scripts |
| **OpenAI API key** | ~$0.50/episode | Text-to-speech (the actual voices) |
| **Matrix server** | Free (self-hosted) or free account | Chat interface to control the bot |
| **Cloudflare domain** | ~$10/year | Serves your podcast RSS feed publicly |
| **A Windows PC** | You have one | Runs everything |

---

## Full Setup Guide (Windows)

### Step 1: Install Prerequisites

#### 1a. Install Python 3.11+

1. Download from https://www.python.org/downloads/
2. **CHECK "Add Python to PATH"** during install
3. Open PowerShell and verify:
   ```powershell
   python --version
   ```

#### 1b. Install ffmpeg

1. Download from https://www.gyan.dev/ffmpeg/builds/ → `ffmpeg-release-essentials.zip`
2. Extract to `C:\ffmpeg`
3. Add `C:\ffmpeg\bin` to your system PATH:
   - Press `Win+R` → type `sysdm.cpl` → Advanced → Environment Variables
   - Under "System variables", find `Path`, click Edit → New → `C:\ffmpeg\bin`
4. Verify in a **new** PowerShell window:
   ```powershell
   ffmpeg -version
   ```

#### 1c. Install Git

1. Download from https://git-scm.com/download/win
2. Install with defaults
3. Verify:
   ```powershell
   git --version
   ```

#### 1d. Install Ollama (Local LLM)

1. Download from https://ollama.com/download/windows
2. Install and let it start
3. Pull a model (open PowerShell):
   ```powershell
   ollama pull llama3.1
   ```
   This downloads ~4.7 GB. If your PC has less than 8GB RAM, use the smaller model:
   ```powershell
   ollama pull llama3.2
   ```
   Then set `OLLAMA_MODEL=llama3.2` in your `.env` file later.

4. Verify it's running:
   ```powershell
   ollama list
   ```
   You should see `llama3.1` (or `llama3.2`) listed.

> **Note:** Ollama runs as a background service on Windows. It starts automatically on boot. The API runs at `http://localhost:11434`.

---

### Step 2: Get an OpenAI API Key

1. Go to https://platform.openai.com/signup and create an account
2. Go to https://platform.openai.com/api-keys
3. Click "Create new secret key", name it "PodcastBot"
4. Copy the key (starts with `sk-`) — you'll need this for `.env`
5. Add billing: https://platform.openai.com/account/billing — add $5-10 to start

> **Cost:** Each podcast episode uses ~$0.30-0.80 in TTS depending on length.

---

### Step 3: Set Up Matrix (Chat Interface)

Matrix is a free, self-hosted chat protocol. You'll use it to send article links to your bot and trigger podcast generation.

#### Option A: Use a Free Public Matrix Server (Easiest)

1. Go to https://app.element.io and click "Create Account"
2. Choose the default server (`matrix.org`) or pick one from https://servers.joinmatrix.org
3. Create your personal account (e.g., `@yourname:matrix.org`)

Now create a bot account:

4. Open a private/incognito browser window
5. Go to https://app.element.io again and create a **second** account for the bot (e.g., `@podcastbot:matrix.org`)
6. From your **personal** account, create a new room:
   - Click `+` → "New Room"
   - Name it "PodcastBot"
   - Make it private
7. Invite your bot account to the room
8. From the **bot** account, accept the invite

Now get the bot's access token:

9. In Element (logged in as the bot), go to Settings → Help & About → scroll down → click "Access Token" (under Advanced)
10. Copy it — this goes in your `.env` file

Get the room ID:

11. In Element, go to the PodcastBot room → Room Settings (gear icon) → Advanced → "Internal room ID"
12. It looks like `!AbCdEfGhIjK:matrix.org` — copy it

#### Option B: Self-Host Matrix with Conduit (Advanced)

If you want your own server, the easiest option is Conduit:

1. Get a VPS ($5/mo from Hetzner, DigitalOcean, or Vultr)
2. Follow https://conduit.rs/deployment/ for Docker setup
3. Point your domain's `matrix.` subdomain to the VPS
4. Create accounts and rooms as above

---

### Step 4: Clone and Configure PodcastBot

```powershell
cd C:\Users\YourName
git clone https://github.com/mattforsberg/podcastbot.git
cd podcastbot
```

Create a virtual environment and install dependencies:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Copy the example config and fill it in:

```powershell
copy .env.example .env
notepad .env
```

Fill in your `.env`:

```ini
# Your podcast's name
PODCAST_NAME=My Tech Briefing
PODCAST_AUTHOR=Your Name
PODCAST_DESC=Daily tech news, AI-generated from curated articles.
PODCAST_BASE_URL=https://podcast.yourdomain.com

# LLM — Ollama is default (free, local)
LLM_PROVIDER=ollama
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1

# OpenAI for text-to-speech
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx

# Matrix (from Step 3)
MATRIX_HOMESERVER=https://matrix.org
MATRIX_ACCESS_TOKEN=syt_xxxxxxxxxxxxxxxxx
MATRIX_USER_ID=@podcastbot:matrix.org
MATRIX_ROOM_ID=!xxxxxxxxxxxxx:matrix.org
```

---

### Step 5: Test It

#### Quick test without Matrix:

```powershell
# Make sure venv is active
.\venv\Scripts\Activate.ps1

# Add an article
python add_article.py https://arstechnica.com/some-article-url

# Generate a podcast
python generate_now.py
```

This will:
1. Fetch the article and summarize it (via Ollama)
2. Research deeper context (via Ollama)
3. Write a two-host script (via Ollama)
4. Generate speech audio (via OpenAI)
5. Assemble into an MP3 in `data/podcast/episodes/`

#### Start the full Matrix-integrated service:

```powershell
python -m podcastbot
```

Then open Element (or your Matrix client) and in the PodcastBot room:
- Paste any article URL → bot fetches and queues it
- Type `status` → see how many articles are queued
- Type `list` → see all queued articles
- Type `podcast` → generate an episode from queued articles
- Type `digest now` → get a written summary instead

---

### Step 6: Set Up Your Domain with Cloudflare (Podcast Hosting)

Your podcast needs a public URL so podcast apps can find the RSS feed.

#### 6a. Buy a Domain

1. Go to https://dash.cloudflare.com and create an account
2. Go to "Domain Registration" → "Register Domain"
3. Search for a domain (e.g., `yourdomain.com`) — most `.com` domains are ~$10/year
4. Purchase it

#### 6b. Set Up Cloudflare Tunnel (Free, No Port Forwarding)

Cloudflare Tunnel lets you expose your local podcast server to the internet without opening ports on your router.

1. In Cloudflare Dashboard → Zero Trust → Networks → Tunnels
2. Click "Create a tunnel"
3. Name it "podcastbot"
4. Choose "Cloudflared" connector
5. Download and install `cloudflared` for Windows:
   ```powershell
   winget install Cloudflare.cloudflared
   ```
6. Run the install command Cloudflare gives you (it looks like):
   ```powershell
   cloudflared service install <your-token>
   ```
7. Configure the tunnel's public hostname:
   - Subdomain: `podcast`
   - Domain: `yourdomain.com`
   - Service: `http://localhost:8085`

Now `https://podcast.yourdomain.com` routes to your local podcast server.

#### 6c. Start the Podcast HTTP Server

```powershell
# In a separate PowerShell window
.\venv\Scripts\Activate.ps1
python -m podcastbot.serve
```

This serves your RSS feed at `https://podcast.yourdomain.com/feed.xml` and episodes at `https://podcast.yourdomain.com/episodes/`.

---

### Step 7: Subscribe in Your Podcast App

Add this RSS feed URL to any podcast app:

```
https://podcast.yourdomain.com/feed.xml
```

Works with:
- **Apple Podcasts** → Library → ••• → Add by URL
- **Spotify** (via Podcasters portal, requires submission)
- **Pocket Casts** → Search → "Feed URL"
- **Overcast** → Add Podcast → "Add URL"
- **Google Podcasts** → Add by RSS
- Any podcast app that supports custom RSS feeds

---

### Step 8: Run as a Background Service (Optional)

#### Using Task Scheduler (Windows)

1. Open Task Scheduler (`Win+R` → `taskschd.msc`)
2. Create two tasks:

**Task 1: PodcastBot Service**
- Trigger: At system startup
- Action: Start a program
  - Program: `C:\Users\YourName\podcastbot\venv\Scripts\python.exe`
  - Arguments: `-m podcastbot`
  - Start in: `C:\Users\YourName\podcastbot`

**Task 2: Podcast HTTP Server**
- Trigger: At system startup
- Action: Start a program
  - Program: `C:\Users\YourName\podcastbot\venv\Scripts\python.exe`
  - Arguments: `-m podcastbot.serve`
  - Start in: `C:\Users\YourName\podcastbot`

For both tasks: check "Run whether user is logged on or not" and "Run with highest privileges".

---

## Architecture

```
You (Matrix client)
  │
  ▼
Matrix Room ──► PodcastBot Service (polls for messages)
                  │
                  ├─ Article URL detected → fetch + summarize (Ollama)
                  │
                  ├─ "podcast" command:
                  │    1. Research each article (Ollama)
                  │    2. Write two-host script (Ollama)
                  │    3. Text-to-speech (OpenAI API)
                  │    4. Assemble MP3 (ffmpeg)
                  │    5. Update RSS feed
                  │
                  ▼
Podcast HTTP Server (port 8085)
  │
  ▼
Cloudflare Tunnel → https://podcast.yourdomain.com
  │
  ▼
Podcast Apps (Apple, Pocket Casts, etc.)
```

## Commands

| Command | What it does |
|---------|-------------|
| `<any URL>` | Fetches article, summarizes, adds to queue |
| `podcast` | Generates episode from all queued articles |
| `status` | Shows article count and episode count |
| `list` | Lists all articles queued this week |
| `digest now` | Generates a written digest (not audio) |

## File Structure

```
podcastbot/
├── .env                    # Your config (not committed)
├── .env.example            # Template
├── requirements.txt        # Python dependencies
├── add_article.py          # CLI: add article without Matrix
├── generate_now.py         # CLI: generate podcast without Matrix
├── podcastbot/
│   ├── config.py           # Loads .env, LLM client
│   ├── matrix.py           # Matrix chat client
│   ├── db.py               # SQLite article storage
│   ├── fetcher.py          # Web scraping + summarization
│   ├── researcher.py       # Deep article analysis
│   ├── scriptwriter.py     # Two-host script generation
│   ├── tts.py              # OpenAI text-to-speech
│   ├── podcast.py          # MP3 assembly + RSS feed
│   ├── digest.py           # Written digest generator
│   ├── serve.py            # HTTP server for podcast files
│   └── service.py          # Main Matrix polling service
└── data/                   # Created at runtime
    ├── podcastbot.db       # SQLite database
    └── podcast/
        ├── feed.xml        # RSS feed
        ├── episodes/       # MP3 files
        └── assets/         # Intro jingle
```

## Costs

| Service | Cost |
|---------|------|
| Ollama (local LLM) | Free |
| OpenAI TTS | ~$0.30-0.80/episode |
| Cloudflare domain | ~$10/year |
| Cloudflare Tunnel | Free |
| Matrix (matrix.org) | Free |

**Total: ~$10/year + ~$0.50/episode**

## Troubleshooting

**"Ollama not responding"**
- Make sure Ollama is running: check system tray or run `ollama serve` in PowerShell
- Test: `curl http://localhost:11434/api/tags` (or open that URL in browser)

**"TTS failed"**
- Check your OpenAI API key is correct in `.env`
- Check you have billing set up at https://platform.openai.com/account/billing

**"ffmpeg not found"**
- Make sure `C:\ffmpeg\bin` is in your system PATH
- Restart PowerShell after changing PATH

**"Matrix connection failed"**
- Verify your access token hasn't expired
- Check the homeserver URL includes `https://`
- Make sure the bot account has joined the room

**Script generation returns empty**
- Ollama may be running out of memory. Try a smaller model: `ollama pull llama3.2`
- Update `OLLAMA_MODEL=llama3.2` in `.env`

## Alternative: Use OpenRouter Instead of Ollama

If your PC can't run Ollama (needs 8GB+ RAM), use OpenRouter's cloud LLMs instead:

1. Go to https://openrouter.ai and create an account
2. Add credits ($5 to start)
3. Get your API key from https://openrouter.ai/keys
4. Update `.env`:
   ```ini
   LLM_PROVIDER=openrouter
   OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxx
   OPENROUTER_MODEL=deepseek/deepseek-chat
   ```

DeepSeek is very cheap (~$0.001/article). Total cost per episode: ~$0.50.

## License

MIT
