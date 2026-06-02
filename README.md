# Local Deal Finder

A personal tool that automatically discovers food and restaurant deals from Reddit, processes them using Claude AI, and surfaces them in a clean card-based web feed timed around meal times. Built for the GTA/Mississauga area.

## Tech Stack

| Layer | Technology |
|---|---|
| Data Collection | Python + PRAW (Reddit API) |
| AI Classification | Claude Haiku |
| AI Extraction | Claude Sonnet |
| Scheduler | APScheduler (runs 4x daily) |
| Database | SQLite |
| Backend | FastAPI |
| Frontend | React + Tailwind CSS |

## Project Structure

```
local-deal-finder/
├── collector/        # Reddit scraper (PRAW)
├── filter/           # Keyword filter before AI calls
├── ai/               # Haiku classifier + Sonnet extractor
├── database/         # SQLite models and read/write logic
├── scheduler/        # Pipeline schedule (6am, 11am, 4pm, 9pm)
├── api/              # FastAPI routes
├── frontend/         # React + Tailwind UI
├── config.py         # All settings: subreddits, keywords, API keys
└── main.py           # Entry point
```

## Getting Started

### Prerequisites
- Python 3.13+
- Node.js (for the frontend — added later)
- A Reddit account (to create API credentials)
- An Anthropic API key

### Setup

1. **Clone the repo**
   ```
   git clone https://github.com/RyanH1919/local-deal-finder.git
   cd local-deal-finder
   ```

2. **Create and activate a virtual environment**
   ```
   python -m venv .venv
   .venv\Scripts\Activate.ps1      # Windows
   source .venv/bin/activate        # Mac/Linux
   ```
   You'll see `(.venv)` in your terminal when it's active.

3. **Install dependencies**
   ```
   pip install -r requirements.txt
   ```

4. **Set up environment variables**

   Create a `.env` file in the root of the project (this file is gitignored — never commit it):
   ```
   REDDIT_CLIENT_ID=your_id_here
   REDDIT_CLIENT_SECRET=your_secret_here
   REDDIT_USER_AGENT=local-deal-finder/1.0
   ANTHROPIC_API_KEY=your_key_here
   ```

5. **Run the app**
   ```
   python main.py
   ```

## API Keys Needed

- **Reddit API** — Create an app at reddit.com/prefs/apps (select "script" type)
- **Anthropic API** — Get a key at console.anthropic.com

## Pipeline Flow

```
Reddit posts → Keyword filter → Haiku (yes/no/uncertain) → Sonnet (extract fields) → SQLite → FastAPI → React feed
```