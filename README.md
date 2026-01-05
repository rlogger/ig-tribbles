# IG-tribbles (dribbles) 

A Discord bot that tracks your Instagram followers and following over time using CSV exports.

## Features

- DM support and auto-detection of CSV uploads
- Track who followed/unfollowed you between uploads
- Visualizations of trends, growth rates, and relationships
- Search for specific users in your data

## Commands

| Command | Description |
|---------|-------------|
| `/upload` | Upload your Instagram CSV file |
| `/stats` | View your dashboard |
| `/trend` | See follower count trend |
| `/growth` | View growth rate between uploads |
| `/changes` | See changes from last upload |
| `/nonfollowers` | See people you don't follow back |
| `/breakdown` | View pie chart of relationships |
| `/history` | View upload history |
| `/search` | Search for a username |

## Setup

### 1. Create Discord Bot

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create new application → Add Bot → Copy token
3. Enable "Message Content Intent"

### 2. Invite Bot

1. Go to OAuth2 → URL Generator
2. Select scopes: `bot`, `applications.commands`
3. Select permissions: `Send Messages`, `Attach Files`, `Embed Links`, `Use Slash Commands`
4. Copy the generated URL and open it to invite the bot

### 3. Install & Run

See [Development Setup](#development-setup) below for nix-shell or manual installation.

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
├── shell.nix        # Nix development environment
├── Dockerfile       # Container configuration
├── docker-compose.yml # Local Docker deployment
├── DEPLOY_GCP.md    # GCP deployment guide
├── .env.example     # Environment template
└── README.md        # This file
```

## Development Setup

### Option 1: Nix Shell (Recommended)

If you have [Nix](https://nixos.org/download.html) installed:

```bash
# Enter the development environment
nix-shell

# Everything is ready! Run the bot:
bot   # or: python bot.py
```

The nix shell includes:
- Python 3.11 with all dependencies
- Neovim with custom config (auto-downloaded)
- Docker & docker-compose
- Git tools (lazygit, etc.)

**Aliases available in nix-shell:**
```bash
bot       # Run the Discord bot
nvim      # Neovim with custom config
lg        # LazyGit
dcup      # docker-compose up -d
dcdown    # docker-compose down
dclogs    # docker-compose logs -f
```

### Option 2: Manual Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your Discord bot token

# Run the bot
python bot.py
```

## Deployment

1. Instagram → Settings → Your Activity → Download Your Information
2. Select "Followers and following" → Format: **CSV**
3. Upload the CSV to the bot

## Usage
```bash
# With nix-shell
nix-shell
bot

# With Docker
docker-compose up -d
docker-compose logs -f
```

## Data Storage

All data stored in `follower_data.db` (SQLite), isolated per user.

## License

MIT
