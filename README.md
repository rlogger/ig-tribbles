# Instagram Ratio Balancer

A Discord bot that helps you track your Instagram followers and following over time using CSV exports.

## Features

- **DM Support**: Chat directly with the bot in DMs - just drop your CSV file!
- **Auto-Detection**: Simply upload a CSV and the bot automatically processes it
- **CSV Upload**: Upload your Instagram followers/following CSV exports
- **Change Tracking**: See who followed/unfollowed you between uploads
- **Visualizations**: Beautiful plots showing trends, growth rates, and relationship breakdowns
- **Historical Data**: Keep a record of all your uploads
- **Search**: Find specific users in your data

## Commands

| Command | Description |
|---------|-------------|
| `/upload` | Upload your Instagram CSV file (followers or following) |
| `/stats` | View your comprehensive dashboard with all statistics |
| `/trend` | See your follower count trend over time |
| `/growth` | View growth rate between uploads |
| `/changes` | See detailed changes from your last upload |
| `/nonfollowers` | See people following you that you don't follow back |
| `/breakdown` | View pie chart of follow relationships |
| `/history` | View your upload history |
| `/search` | Search for a specific username |
| `/help` | Show all available commands |

## Setup

### 1. Create a Discord Bot

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application" and give it a name
3. Go to "Bot" section and click "Add Bot"
4. Copy the bot token
5. Enable "Message Content Intent" under Privileged Gateway Intents

### 2. Invite the Bot

1. Go to OAuth2 → URL Generator
2. Select scopes: `bot`, `applications.commands`
3. Select permissions: `Send Messages`, `Attach Files`, `Embed Links`, `Use Slash Commands`
4. Copy the generated URL and open it to invite the bot

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment

```bash
cp .env.example .env
# Edit .env and add your Discord bot token
```

### 5. Run the Bot

```bash
python bot.py
```

## How to Export Instagram Data

1. Open Instagram app or website
2. Go to Settings → Your Activity → Download Your Information
3. Select "Some of your information"
4. Choose "Followers and following"
5. Select format: **CSV**
6. Download and upload the CSV file to Discord

## Quick Start (DM the Bot)

Once the bot is running, you can DM it directly:

1. Find the bot and click to open a DM
2. Say `hi` or `help` to see what it can do
3. **Just drop your CSV file** - the bot automatically processes it!
4. Type `stats`, `changes`, or `history` for quick info

## Project Structure

```
ig-discord/
├── bot.py           # Main Discord bot
├── database.py      # SQLite database operations
├── csv_parser.py    # CSV parsing utilities
├── plotting.py      # Matplotlib visualizations
├── requirements.txt # Python dependencies
├── Dockerfile       # Container configuration
├── docker-compose.yml # Local Docker deployment
├── DEPLOY_GCP.md    # GCP deployment guide
├── .env.example     # Environment template
└── README.md        # This file
```

## Deployment

### Local with Docker

```bash
# Build and run
docker-compose up -d

# View logs
docker-compose logs -f
```

### Google Cloud Platform

See [DEPLOY_GCP.md](DEPLOY_GCP.md) for detailed instructions on deploying to:
- Google Compute Engine (recommended, free tier eligible)
- Cloud Run (managed, always-on)
- Google Kubernetes Engine (for complex setups)

## Data Storage

All data is stored locally in `follower_data.db` (SQLite). Each user's data is isolated by their Discord user ID and server ID.

## License

MIT
