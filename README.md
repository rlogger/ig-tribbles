# IG-tribbles (dribbles)

A Discord bot to track your Instagram followers, see who unfollowed you, and manage pending follow requests.

## Features

- **Drop & Go**: Just drop your CSV file in DMs - no commands needed
- **Change Tracking**: See who followed/unfollowed between uploads
- **Visualizations**: Trend charts, pie charts, growth rates
- **Requested Tracking**: Keep track of pending follow requests
- **Search**: Find specific users in your data

## Quick Start

```bash
# Using nix (recommended)
nix-shell
bot

# Or manually
pip install -r requirements.txt
cp .env.example .env  # Add your DISCORD_TOKEN
python bot.py
```

## Commands

### Follower Analysis
| Command | Description |
|---------|-------------|
| `/upload` | Upload followers/following CSV |
| `/stats` | Dashboard with all stats |
| `/changes` | Who followed/unfollowed |
| `/trend` | Follower count over time |
| `/growth` | Growth rate between uploads |
| `/breakdown` | Pie chart of relationships |
| `/nonfollowers` | Fans you don't follow back |
| `/search` | Find a username |
| `/history` | Past uploads |
| `/demo` | Load sample data |

### Requested Tracking
| Command | Description |
|---------|-------------|
| `/requested` | View pending follow requests |
| `/requested_add` | Add usernames (comma/space/newline separated) |
| `/requested_remove` | Remove usernames |
| `/requested_check` | Check who accepted (compare with followers) |
| `/requested_clear` | Clear entire list |

### DM Commands
Just message the bot directly:
- Drop a CSV file (auto-processed)
- `stats` / `changes` / `history`
- `hi` or `help` for instructions

## Setup

### 1. Create Discord Bot

1. [Discord Developer Portal](https://discord.com/developers/applications) → New Application
2. Bot → Add Bot → Copy token
3. Enable **Message Content Intent**

### 2. Invite Bot

OAuth2 → URL Generator:
- Scopes: `bot`, `applications.commands`
- Permissions: `Send Messages`, `Attach Files`, `Embed Links`

### 3. Get Instagram Data

1. Instagram → Settings → Accounts Center
2. Your information and permissions → Download your information
3. Select account → Download or transfer information
4. Some of your information → **Followers and following**
5. Download to device → **CSV format**

## Development

### Nix Shell (Recommended)

```bash
nix-shell
```

Includes Python 3.11, all dependencies, Neovim, Docker, lazygit.

**Aliases:**
```bash
bot       # Run bot
nvim      # Neovim with config
lg        # LazyGit
dcup      # docker-compose up -d
dcdown    # docker-compose down
dclogs    # docker-compose logs -f
```

### Manual

```bash
pip install -r requirements.txt
cp .env.example .env
python bot.py
```

## Deployment

### Docker

```bash
docker-compose up -d
docker-compose logs -f
```

### GCP

See [DEPLOY_GCP.md](DEPLOY_GCP.md) for:
- Google Compute Engine (free tier)
- Cloud Run
- GKE

## Project Structure

```
ig-discord/
├── bot.py              # Discord bot
├── database.py         # SQLite operations
├── csv_parser.py       # CSV parsing
├── plotting.py         # Matplotlib charts
├── shell.nix           # Nix environment
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

## License

MIT
