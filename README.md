# IG-tribbles (dribbles)

A Discord bot to check your instagram 

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
- Drop a CSV file (auto-processed)
- `stats` / `changes` / `history`
- `hi` or `help` for instructions

