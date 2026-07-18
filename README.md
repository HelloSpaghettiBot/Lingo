# Modern Discord Community Bot

A modern `discord.py` community-management bot that builds and maintains a structured multilingual Discord server.

The bot can create the server layout, welcome new members, give members self-service language roles, restrict language channels to the correct roles, clean up messages, report its status, and generate setup instructions for a separate translation bot. All user-facing commands use Discord slash commands.

## What the bot does

### Builds a complete community server

Running `/setup` creates or repairs a ready-to-use Discord server structure containing important information channels, general discussion channels, voice channels, gaming rooms, language roles, and private language channels.

The setup command is idempotent. It looks for existing categories, channels, and roles before creating anything, so administrators can run it again to restore missing pieces or repair permissions without intentionally duplicating the entire layout.

### Creates self-service language roles

The bot creates a Discord role for every supported language and posts a persistent language-selection menu in the role channel.

Members can select one or several languages from the menu. The bot then:

- Adds the selected language roles.
- Removes language roles that are no longer selected.
- Gives the member access to the matching private language channels.
- Replies privately so the role-channel is not filled with confirmation messages.

Members can also manage their roles through `/language add`, `/language remove`, and `/language clear`.

### Creates private language channels

Each language receives its own text channel. The language category is hidden from the default `@everyone` role. A member can see a language channel only after receiving its matching role.

The bot itself is granted access so it can maintain those channels and their permission overwrites.

### Welcomes new members

When someone joins, the bot posts a welcome message in the configured welcome channel and directs the member to the configured language-role channel.

The welcome and role channels can be selected when `/setup` is run. If no channels are supplied, the bot uses the channels it creates automatically.

### Provides message cleanup

Members with the **Manage Messages** permission can run `/clear` in a text channel or thread. The command can remove between 1 and 500 recent messages and reports the result privately.

### Provides built-in help and status reporting

`/help` shows the available administration and member commands.

`/status` reports:

- Current Discord API latency.
- Installed `discord.py` version.
- Number of configured language roles.
- Configured welcome channel.
- Configured role-selection channel.

### Supports multiple Discord servers

Configuration is stored separately for every server by guild ID. One running bot instance can therefore serve multiple Discord servers without mixing their welcome channels, role messages, role IDs, or language-channel IDs.

### Keeps the language menu working after restarts

The language selector is registered as a persistent Discord UI view. Its fixed component ID and unlimited view lifetime allow an existing selector message to continue handling selections after the bot restarts.

The original selector message must still exist, and the bot must still have permission to read the channel and manage the roles.

## Server structure created by `/setup`

### Important

Category:

```text
💳 | ==== Important ==== | 💳
```

Text channels:

```text
👋・welcome
📜・rules
📣・announcements
📦・resources
🤖・get-roles
```

`👋・welcome` is the default new-member welcome channel.

`🤖・get-roles` is the default location for the persistent language-selection menu.

### Thought Chambers

Category:

```text
👥 | ====== Thought Chambers ====== | 👥
```

Text channels:

```text
💬・general
👥・debate
🧪・science
✝️・religion
🏺・history
🚧・projects
📬・off-topic
```

### Voice

Category:

```text
🔊 | ====== Voice ====== | 🔊
```

Voice channels:

```text
🔊・Lounge
🎵・Music
📅・Meeting
🎮・Gaming
💤・AFK
```

### Playing Rooms

Category:

```text
🌀 | === Playing Rooms === | 🌀
```

Voice channels:

```text
🌀・Duos
🌀・Trios
🌀・Squads
```

### Language Zones

Category:

```text
🌍 | Language Zones | 🌍
```

Private text channels:

```text
🗣・english
🗣・mandarin
🗣・hindi
🗣・spanish
🗣・french
🗣・arabic
🗣・bengali
🗣・russian
🗣・portuguese
🗣・urdu
```

## Supported languages

The bot currently creates these roles and channels:

| Flag | Language | Role name | Channel |
|---|---|---|---|
| 🇬🇧 | English | `English` | `🗣・english` |
| 🇨🇳 | Mandarin | `Mandarin` | `🗣・mandarin` |
| 🇮🇳 | Hindi | `Hindi` | `🗣・hindi` |
| 🇪🇸 | Spanish | `Spanish` | `🗣・spanish` |
| 🇫🇷 | French | `French` | `🗣・french` |
| 🇸🇦 | Arabic | `Arabic` | `🗣・arabic` |
| 🇧🇩 | Bengali | `Bengali` | `🗣・bengali` |
| 🇷🇺 | Russian | `Russian` | `🗣・russian` |
| 🇵🇹 | Portuguese | `Portuguese` | `🗣・portuguese` |
| 🇵🇰 | Urdu | `Urdu` | `🗣・urdu` |

## Slash commands

### `/setup`

Creates or repairs the server layout and language-role system.

Permission required: **Administrator**

Options:

- `welcome_channel` — optional channel for new-member welcome messages.
- `role_channel` — optional channel where the language selector should be posted.

When the options are omitted, the bot uses `👋・welcome` and `🤖・get-roles`.

The command:

1. Checks the bot's required permissions.
2. Creates any missing categories.
3. Creates any missing text and voice channels.
4. Creates any missing language roles.
5. Hides the language category from `@everyone`.
6. Grants each language role access to its corresponding channel.
7. Creates or updates the language-selector message.
8. Saves all relevant IDs in `config.json`.
9. Reports whether it created missing items or reused the existing structure.

The command also warns the administrator when a language role is above the bot's highest role and therefore cannot be managed.

### `/clear`

Deletes recent messages from the current text channel or thread.

Permission required: **Manage Messages**

Option:

- `amount` — number of messages to remove, from 1 to 500. Defaults to 100.

The result is sent ephemerally and is visible only to the person who ran the command.

### `/language add`

Adds one supported language role to the member running the command.

Option:

- `language` — one of the supported language choices.

### `/language remove`

Removes one supported language role from the member running the command.

Option:

- `language` — one of the supported language choices.

### `/language clear`

Removes every supported language role currently assigned to the member running the command.

### `/setup_translations`

Produces a private checklist showing which translation-bot command an administrator should manually run in each configured language channel.

Permission required: **Administrator**

This command does not translate messages and does not execute another bot's slash commands. Discord does not allow this bot to invoke another application's slash command merely by posting command-shaped text.

### `/help`

Displays the bot's administration and member commands in an ephemeral embed.

### `/status`

Displays the bot's connection and setup status in an ephemeral embed.

## Language-selector behavior

The selector supports multiple simultaneous choices. Submitting it makes the selected values authoritative:

- Newly selected roles are added.
- Previously held language roles that are no longer selected are removed.
- Other unrelated Discord roles are never changed.

The menu requires at least one selection. Members who want to remove every language role should use `/language clear`.

Role changes can fail when:

- The bot lacks **Manage Roles**.
- The bot's highest role is below or equal to a language role.
- The language roles were deleted or renamed after setup.
- Discord denies the operation or the bot loses access to the server.

Running `/setup` again can recreate missing roles and repair most channel permissions. The bot's own role position must be corrected manually in Discord's **Server Settings → Roles** page.

## Requirements

- Python 3.10 or newer.
- A Discord bot application and token.
- `discord.py` 2.7.1.
- `python-dotenv` 1.2.2.
- Permission to invite and configure a bot in the target server.

Python dependencies are listed in `requirements.txt`.

## Discord Developer Portal setup

### 1. Create the application

1. Open the Discord Developer Portal.
2. Create a new application.
3. Open the application's **Bot** section.
4. Create the bot user if Discord has not already created it.
5. Reset or copy the bot token.
6. Never post the token publicly or commit it to GitHub.

### 2. Enable the required intent

Under **Bot → Privileged Gateway Intents**, enable:

- **Server Members Intent**

This is required for the new-member welcome event and reliable member-role handling.

**Message Content Intent is not required.** The bot uses slash commands and does not inspect ordinary message content.

### 3. Generate the invite

In the Developer Portal's OAuth2 URL generator, select both scopes:

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

Administrator permission will also cover these capabilities, but granting only the permissions the bot actually needs is safer.

### 4. Correct the role hierarchy

After inviting the bot:

1. Open **Server Settings → Roles**.
2. Find the bot's role.
3. Move it above all language roles.

Discord never allows a bot to add, remove, edit, or otherwise manage a role that is at or above its own highest role, even when the bot has **Manage Roles** or **Administrator**.

## Windows installation

The package includes `run_bot.bat` for Windows.

1. Install Python 3.10 or newer and enable **Add Python to PATH** during installation.
2. Extract the bot ZIP into a permanent folder.
3. Double-click `run_bot.bat`.
4. On the first run, the script creates a Python virtual environment, installs dependencies, creates `.env`, and stops.
5. Open `.env` in Notepad.
6. Replace `replace_with_your_bot_token` with the actual Discord bot token.
7. Save the file.
8. Double-click `run_bot.bat` again.
9. Wait for the console to report that the bot has logged in and synchronized its commands.
10. In Discord, run `/setup` in the target server.

Keep the console window open while the bot is running. Closing it stops the bot.

## Manual installation

### Windows PowerShell

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
python bot.py
```

### Linux or macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cp .env.example .env
nano .env
python bot.py
```

## Environment configuration

The bot reads settings from `.env`.

```dotenv
DISCORD_TOKEN=replace_with_your_bot_token
DISCORD_GUILD_ID=
BOT_CONFIG_PATH=config.json
LOG_LEVEL=INFO
```

### `DISCORD_TOKEN`

Required. The secret token from the Discord Developer Portal.

Do not wrap it in quotes unless the token itself requires them. Do not publish this file.

### `DISCORD_GUILD_ID`

Optional development server ID.

When set, the bot copies its commands into that one server and synchronizes them there. Guild commands usually appear much faster, which is useful while developing or testing changes.

When empty, the bot synchronizes commands globally for every server where it is installed. Global command changes can take longer to appear throughout Discord.

To copy a server ID, enable Discord **Developer Mode**, right-click the server, and select **Copy Server ID**.

### `BOT_CONFIG_PATH`

Optional path to the JSON configuration file. Defaults to:

```text
config.json
```

A relative path is resolved from the folder in which the bot is launched.

### `LOG_LEVEL`

Optional console logging level. Defaults to `INFO`.

Common values:

```text
DEBUG
INFO
WARNING
ERROR
CRITICAL
```

Use `DEBUG` when troubleshooting development issues. It produces considerably more console output.

## Configuration storage

The bot creates `config.json` automatically. It stores Discord object IDs, not message content or user conversations.

Stored per server:

- Welcome-channel ID.
- Language-role channel ID.
- Persistent selector-message ID.
- Supported language role IDs.
- Supported language channel IDs.

Writes are protected by an asynchronous lock and use an atomic temporary-file replacement to reduce the chance of corruption during concurrent updates or an interrupted write.

Back up `config.json` when moving the bot to another machine. If it is deleted, run `/setup` again so the bot can rediscover or recreate the necessary structure.

The bot can migrate the old single-server welcome-channel setting when an old flat `config.json` is present and the bot is connected to exactly one server. Run `/setup` afterward to populate the complete modern configuration.

## Included files

```text
modern_discord_bot/
├── .env.example       Example environment configuration
├── bot.py             Main bot source code
├── README.md          Complete usage and feature documentation
├── requirements.txt   Pinned Python dependencies
└── run_bot.bat        Windows setup and launch script
```

Files generated after running the bot are intentionally not included in the package:

```text
.env                   Private local environment settings and bot token
.venv/                 Local Python virtual environment
config.json            Per-server runtime configuration
__pycache__/           Python bytecode cache
```

## Security and safety behavior

- The token is loaded from `.env` rather than hardcoded in `bot.py`.
- The bot does not require Message Content Intent.
- It does not read or store normal server messages.
- It prevents accidental `@everyone` and role mentions through restricted allowed-mention settings.
- Administrative slash commands use Discord permission checks.
- Most command responses are ephemeral to reduce channel clutter and avoid exposing operational details.
- Errors are logged to the console while members receive a safe, concise failure message.

If a real token is ever exposed in code, a screenshot, chat, GitHub, or a public file, reset it immediately in the Discord Developer Portal.

## What the bot does not do

This project currently does not provide:

- Automatic message translation.
- Automatic execution of another bot's slash commands.
- Moderation commands such as ban, kick, timeout, warn, mute, or automod.
- Audit-log tracking or moderation logs.
- Ticketing or support-ticket channels.
- Leveling, XP, currency, games, music playback, or economy features.
- Reaction-role handling; the modern selector and slash commands replace it.
- A web dashboard.
- A database server; configuration is stored in local JSON.
- Automatic backups of `.env` or `config.json`.
- Automatic hosting as a Windows service, Linux service, Docker container, or cloud deployment.
- Runtime commands for creating arbitrary new languages. Supported languages are defined in `bot.py`.
- Custom welcome-message editing through Discord commands.
- Deletion of more than 500 messages in one `/clear` request.
- Recovery of a deleted role-selector message without running `/setup` again.

These limitations are deliberate descriptions of the current build, not claims that Discord cannot support those features.

## Customizing the bot

The main server structure is defined near the beginning of `bot.py` in these constants:

```python
LANGUAGES
IMPORTANT_CATEGORY
IMPORTANT_CHANNELS
MAIN_CATEGORY
MAIN_CHANNELS
VOICE_CATEGORY
VOICE_CHANNELS
PLAYING_CATEGORY
PLAYING_CHANNELS
LANGUAGE_CATEGORY
```

Change those values before running `/setup` to customize the generated layout.

When adding a language, add one entry to `LANGUAGES` using the visible role name as the key and the flag emoji as the value. Restart the bot and run `/setup` again.

Important considerations:

- Discord select menus support at most 25 options. The current language menu uses 10.
- Renaming an existing role or channel manually can cause `/setup` to treat the renamed item as missing and create the configured name again.
- Changing a command definition requires restarting the bot so the command tree can synchronize.
- Keep `DISCORD_GUILD_ID` set during development when rapid command updates are important.

## Command synchronization

Commands are synchronized during startup.

When `DISCORD_GUILD_ID` is set:

- Commands are copied and synchronized to that development server.
- Changes normally appear quickly.
- The development commands apply only to that server.

When `DISCORD_GUILD_ID` is empty:

- Commands are synchronized globally.
- They are available in every server that installed the application with the `applications.commands` scope.
- Discord may take longer to display newly created, renamed, or changed commands everywhere.

If commands do not appear, confirm that:

1. The console shows a successful login and synchronization message.
2. The bot was invited with the `applications.commands` scope.
3. `DISCORD_GUILD_ID`, when used, contains the correct numeric server ID.
4. The bot application is actually installed in that server.
5. The bot has been restarted since the command code changed.

## Troubleshooting

### The bot says `DISCORD_TOKEN is missing`

The `.env` file is absent, in the wrong folder, or does not contain a valid `DISCORD_TOKEN` entry.

Create `.env` beside `bot.py` and add:

```dotenv
DISCORD_TOKEN=your_actual_token_here
```

### The bot logs in but slash commands do not appear

Confirm the application was invited with the `applications.commands` scope. During development, place the target server ID in `DISCORD_GUILD_ID`, restart the bot, and review the synchronization line in the console.

### Members cannot select language roles

Check all of the following:

- The bot has **Manage Roles**.
- The bot's role is above every language role.
- `/setup` completed successfully.
- The selector message still exists.
- The member is using the selector inside the server rather than in a DM.

### Members receive a role but cannot see the language channel

Run `/setup` again to repair the category and channel permission overwrites. Also verify that no higher-level manual overwrite denies the member or role access.

### Welcome messages are not sent

Check that:

- **Server Members Intent** is enabled in the Developer Portal.
- The bot was restarted after enabling the intent.
- `/setup` has saved a valid welcome channel.
- The bot can view and send messages in that channel.

### `/clear` fails

The command requires the member to have **Manage Messages**. The bot also needs **Manage Messages** and **Read Message History** in the current channel.

### `/setup` reports missing permissions

Grant the permissions listed in the response. Also inspect category-specific permission overwrites because a server-wide permission can still be blocked in a particular category or channel.

### The console closes immediately on Windows

Run `run_bot.bat` from an existing Command Prompt window so the error remains visible:

```bat
cd C:\path\to\modern_discord_bot
run_bot.bat
```

Common causes are an invalid token, missing Python installation, blocked package installation, or an incorrectly formatted `.env` file.

### Translation setup does not run automatically

That is expected. `/setup_translations` generates a checklist only. An administrator must invoke the separate translation bot's actual slash command in each channel.

## Normal administration workflow

1. Invite the bot with the correct scopes and permissions.
2. Move its role above the language roles.
3. Start the bot.
4. Run `/setup` once.
5. Add rules, announcements, and resources to the generated channels.
6. Configure the external translation bot manually when one is being used.
7. Use `/status` to verify setup.
8. Run `/setup` again after deleting a generated role/channel or changing relevant permissions.
9. Back up `config.json` before migrating the bot installation.

## Starting and stopping

Start on Windows by running:

```text
run_bot.bat
```

Start manually from an activated virtual environment with:

```bash
python bot.py
```

Stop the bot cleanly by focusing the console and pressing:

```text
Ctrl+C
```

The bot must remain running and connected for slash commands, welcomes, role changes, and the persistent selector to work.
