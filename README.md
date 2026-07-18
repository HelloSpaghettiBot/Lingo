# Modern Discord Community Bot

This is a slash-command rewrite of the supplied prefix-command bot. It targets Python 3.10+ and `discord.py` 2.7.1.

## Main changes

- Replaces `!setup`, `!clear`, and the old translation helper with application commands.
- Adds `/language add`, `/language remove`, and `/language clear`.
- Replaces reaction-only language assignment with a persistent multi-select menu that continues working after restarts.
- Removes the privileged Message Content intent because this bot no longer depends on message commands.
- Stores settings per Discord server instead of using one global set of IDs.
- Moves the token out of source code and into `.env`.
- Makes `/setup` idempotent: it creates missing items and reuses or repairs existing ones.
- Uses role-based channel access instead of individual member permission overwrites.
- Adds centralized application-command error handling and structured logging.

## Commands

- `/setup [welcome_channel] [role_channel]` — creates or repairs categories, channels, language roles, permissions, and the persistent role menu.
- `/clear [amount]` — deletes 1–500 recent messages.
- `/language add <language>` — adds one language role.
- `/language remove <language>` — removes one language role.
- `/language clear` — removes all language roles.
- `/setup_translations` — generates a manual checklist for the third-party translation bot.
- `/help` — lists the available slash commands.
- `/status` — reports latency, library version, and setup state.

## Install and run on Windows

1. Install Python 3.10 or newer.
2. Double-click `run_bot.bat` once. It creates `.env` and stops.
3. Open `.env` and replace `replace_with_your_bot_token` with the real bot token.
4. Double-click `run_bot.bat` again.

Manual setup:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
copy .env.example .env
# Edit .env, then:
python bot.py
```

## Discord Developer Portal settings

Under **Bot → Privileged Gateway Intents**, enable **Server Members Intent**. Message Content Intent is not required.

Invite the bot with both scopes:

- `bot`
- `applications.commands`

Recommended bot permissions:

- View Channels
- Send Messages
- Embed Links
- Read Message History
- Manage Channels
- Manage Roles
- Manage Messages

Move the bot's role above every language role. Discord prevents a bot from managing roles at or above its own highest role.

## Command synchronization

For fast development, place one server ID in `DISCORD_GUILD_ID`. Guild command changes usually appear immediately.

For production across multiple servers, leave `DISCORD_GUILD_ID` empty. The bot will sync global commands during startup; Discord may take time to show a newly changed global command everywhere.

## Translation command limitation

The old bot posted text such as `/set_dedicated_lang ...` into a channel. That does not invoke another application's slash command. Discord interactions must be initiated as an interaction by a user or by an integration that directly supports the operation. `/setup_translations` now provides an honest manual checklist instead of reporting false success.

## Existing config migration

If an old flat `config.json` exists and the bot is connected to exactly one server, its saved welcome channel is migrated. Run `/setup` once to create the new per-server role and channel records.
