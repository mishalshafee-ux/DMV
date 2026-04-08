# DMV RP System

Production-ready Discord DMV bot with:
- Economy + banking
- Licenses + driving tests + booking queue
- Staff applications
- Verification
- Police MDT
- Ticket system
- Staff shift tracking
- Digital license cards
- Flask web dashboard with Discord OAuth scaffold
- SQLite backend shared by bot and dashboard

## File Layout

- `bot.py`
- `config.py`
- `database.py`
- `cogs/`
- `utils/`
- `web/`
- `.env`
- `requirements.txt`

## Setup

1. Create a Discord bot in the Discord Developer Portal.
2. Enable:
   - Server Members Intent
   - Message Content Intent
3. Copy `.env.example` to `.env`
4. Fill in:
   - `DISCORD_TOKEN`
   - `GUILD_ID`
   - Discord OAuth2 fields for dashboard
5. Install dependencies:
   ```bash
   pip install -r requirements.txt
