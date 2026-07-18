from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any, Iterable, Optional

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

LOGGER = logging.getLogger("community_bot")
CONFIG_PATH = Path(os.getenv("BOT_CONFIG_PATH", "config.json"))
DEV_GUILD_ID = os.getenv("DISCORD_GUILD_ID")

LANGUAGES: dict[str, str] = {
    "English": "🇬🇧",
    "Mandarin": "🇨🇳",
    "Hindi": "🇮🇳",
    "Spanish": "🇪🇸",
    "French": "🇫🇷",
    "Arabic": "🇸🇦",
    "Bengali": "🇧🇩",
    "Russian": "🇷🇺",
    "Portuguese": "🇵🇹",
    "Urdu": "🇵🇰",
}

IMPORTANT_CATEGORY = "💳 | ==== Important ==== | 💳"
IMPORTANT_CHANNELS = (
    "👋・welcome",
    "📜・rules",
    "📣・announcements",
    "📦・resources",
    "🤖・get-roles",
)

MAIN_CATEGORY = "👥 | ====== Thought Chambers ====== | 👥"
MAIN_CHANNELS = (
    "💬・general",
    "👥・debate",
    "🧪・science",
    "✝️・religion",
    "🏺・history",
    "🚧・projects",
    "📬・off-topic",
)

VOICE_CATEGORY = "🔊 | ====== Voice ====== | 🔊"
VOICE_CHANNELS = (
    "🔊・Lounge",
    "🎵・Music",
    "📅・Meeting",
    "🎮・Gaming",
    "💤・AFK",
)

PLAYING_CATEGORY = "🌀 | === Playing Rooms === | 🌀"
PLAYING_CHANNELS = (
    "🌀・Duos",
    "🌀・Trios",
    "🌀・Squads",
)

LANGUAGE_CATEGORY = "🌍 | Language Zones | 🌍"
LANGUAGE_SELECT_CUSTOM_ID = "community-bot:language-select:v2"

LANGUAGE_CHOICES = [
    app_commands.Choice(name=f"{flag} {language}", value=language)
    for language, flag in LANGUAGES.items()
]


class ConfigStore:
    """Small JSON-backed, per-guild configuration store with atomic writes."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = asyncio.Lock()
        self._data = self._load()

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"version": 2, "guilds": {}}

        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            LOGGER.error("Could not read %s: %s", self.path, exc)
            return {"version": 2, "guilds": {}}

        if isinstance(raw, dict) and isinstance(raw.get("guilds"), dict):
            raw.setdefault("version", 2)
            return raw

        # Preserve the old single-server config so its welcome channel can be
        # migrated automatically when the bot is connected to one guild.
        return {"version": 2, "guilds": {}, "legacy": raw if isinstance(raw, dict) else {}}

    def guild(self, guild_id: int) -> dict[str, Any]:
        guild_data = self._data.get("guilds", {}).get(str(guild_id), {})
        return dict(guild_data) if isinstance(guild_data, dict) else {}

    async def update_guild(self, guild_id: int, **values: Any) -> None:
        async with self._lock:
            guilds = self._data.setdefault("guilds", {})
            guild_data = guilds.setdefault(str(guild_id), {})
            guild_data.update(values)
            await asyncio.to_thread(self._write_atomic)

    async def migrate_legacy(self, guild_id: int) -> None:
        async with self._lock:
            legacy = self._data.get("legacy")
            if not isinstance(legacy, dict) or not legacy:
                return

            guilds = self._data.setdefault("guilds", {})
            guild_data = guilds.setdefault(str(guild_id), {})
            if legacy.get("welcome_channel_id") and not guild_data.get("welcome_channel_id"):
                guild_data["welcome_channel_id"] = legacy["welcome_channel_id"]

            self._data.pop("legacy", None)
            await asyncio.to_thread(self._write_atomic)

    def _write_atomic(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(f"{self.path.suffix}.tmp")
        temporary.write_text(
            json.dumps(self._data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        os.replace(temporary, self.path)


def find_named(items: Iterable[Any], name: str) -> Any | None:
    target = name.casefold()
    return discord.utils.find(lambda item: item.name.casefold() == target, items)


def resolve_role(guild: discord.Guild, language: str, guild_config: dict[str, Any]) -> discord.Role | None:
    role_ids = guild_config.get("language_roles", {})
    if isinstance(role_ids, dict):
        role_id = role_ids.get(language)
        if role_id:
            role = guild.get_role(int(role_id))
            if role is not None:
                return role

    return find_named(guild.roles, language)


def role_is_manageable(guild: discord.Guild, role: discord.Role) -> bool:
    bot_member = guild.me
    return bool(bot_member and role != guild.default_role and bot_member.top_role > role)


def language_embed() -> discord.Embed:
    instructions = (
        "🇬🇧 Select your language or languages\n"
        "🇨🇳 选择你的语言\n"
        "🇮🇳 अपनी भाषा चुनें\n"
        "🇪🇸 Selecciona tu idioma\n"
        "🇫🇷 Choisissez votre langue\n"
        "🇸🇦 اختر لغتك\n"
        "🇧🇩 আপনার ভাষা নির্বাচন করুন\n"
        "🇷🇺 Выберите язык\n"
        "🇵🇹 Escolha seu idioma\n"
        "🇵🇰 اپنی زبان منتخب کریں"
    )
    embed = discord.Embed(
        title="Choose your language roles",
        description=(
            f"{instructions}\n\n"
            "Select every language channel you want access to. "
            "Submitting the menu replaces your existing language selections."
        ),
        colour=discord.Colour.blurple(),
    )
    embed.set_footer(text="You can also use /language add, /language remove, or /language clear.")
    return embed


async def send_ephemeral(interaction: discord.Interaction, content: str) -> None:
    if interaction.response.is_done():
        await interaction.followup.send(content, ephemeral=True)
    else:
        await interaction.response.send_message(content, ephemeral=True)


class LanguageSelect(discord.ui.Select):
    def __init__(self) -> None:
        options = [
            discord.SelectOption(label=language, value=language, emoji=flag)
            for language, flag in LANGUAGES.items()
        ]
        super().__init__(
            custom_id=LANGUAGE_SELECT_CUSTOM_ID,
            placeholder="Select one or more languages",
            min_values=1,
            max_values=len(options),
            options=options,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            await send_ephemeral(interaction, "This menu only works inside a server.")
            return

        member = interaction.user
        if not isinstance(member, discord.Member):
            try:
                member = await interaction.guild.fetch_member(interaction.user.id)
            except discord.HTTPException:
                await send_ephemeral(interaction, "I could not load your server membership.")
                return

        bot = interaction.client
        if not isinstance(bot, CommunityBot):
            await send_ephemeral(interaction, "The bot configuration is unavailable.")
            return

        guild_config = bot.config.guild(interaction.guild.id)
        all_roles = {
            language: resolve_role(interaction.guild, language, guild_config)
            for language in LANGUAGES
        }
        missing = [language for language, role in all_roles.items() if role is None]
        if missing:
            await send_ephemeral(
                interaction,
                "The language roles are not fully configured. An administrator should run `/setup`.",
            )
            return

        selected = set(self.values)
        current_language_roles = {
            role
            for role in all_roles.values()
            if role is not None and role in member.roles
        }
        desired_language_roles = {
            role
            for language, role in all_roles.items()
            if language in selected and role is not None
        }

        roles_to_add = desired_language_roles - current_language_roles
        roles_to_remove = current_language_roles - desired_language_roles
        unmanaged = [
            role.name
            for role in roles_to_add | roles_to_remove
            if not role_is_manageable(interaction.guild, role)
        ]
        if unmanaged:
            await send_ephemeral(
                interaction,
                "I cannot manage these roles because they are above my highest role: "
                + ", ".join(sorted(unmanaged)),
            )
            return

        try:
            if roles_to_add:
                await member.add_roles(*roles_to_add, reason="Language role menu selection")
            if roles_to_remove:
                await member.remove_roles(*roles_to_remove, reason="Language role menu selection")
        except discord.Forbidden:
            await send_ephemeral(
                interaction,
                "I do not have permission to update your roles. Check my Manage Roles permission and role position.",
            )
            return
        except discord.HTTPException as exc:
            LOGGER.exception("Failed to update language roles")
            await send_ephemeral(interaction, f"Discord rejected the role update: {exc}")
            return

        chosen = ", ".join(f"{LANGUAGES[name]} {name}" for name in self.values)
        await send_ephemeral(interaction, f"Your language roles are now: {chosen}")


class LanguageRoleView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)
        self.add_item(LanguageSelect())


class CommunityBot(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.members = True

        super().__init__(
            command_prefix=commands.when_mentioned,
            intents=intents,
            allowed_mentions=discord.AllowedMentions(
                everyone=False,
                roles=False,
                users=True,
                replied_user=False,
            ),
            activity=discord.Game(name="Use /help or /setup"),
        )
        self.config = ConfigStore(CONFIG_PATH)

    async def setup_hook(self) -> None:
        self.add_view(LanguageRoleView())

        if DEV_GUILD_ID:
            guild_object = discord.Object(id=int(DEV_GUILD_ID))
            self.tree.copy_global_to(guild=guild_object)
            synced = await self.tree.sync(guild=guild_object)
            LOGGER.info("Synced %d command(s) to development guild %s", len(synced), DEV_GUILD_ID)
        else:
            synced = await self.tree.sync()
            LOGGER.info("Synced %d global application command(s)", len(synced))


bot = CommunityBot()


async def require_bot_permissions(
    interaction: discord.Interaction,
    *permission_names: str,
) -> bool:
    if interaction.guild is None or interaction.guild.me is None:
        await send_ephemeral(interaction, "This command must be used inside a server.")
        return False

    permissions = interaction.guild.me.guild_permissions
    missing = [
        name.replace("_", " ").title()
        for name in permission_names
        if not getattr(permissions, name, False)
    ]
    if missing:
        await send_ephemeral(
            interaction,
            "I am missing required permissions: " + ", ".join(missing),
        )
        return False
    return True


async def ensure_category(
    guild: discord.Guild,
    name: str,
    created: list[str],
) -> discord.CategoryChannel:
    existing = find_named(guild.categories, name)
    if existing is not None:
        return existing

    category = await guild.create_category(name, reason="Community bot server setup")
    created.append(f"category: {name}")
    return category


async def ensure_text_channel(
    guild: discord.Guild,
    category: discord.CategoryChannel,
    name: str,
    created: list[str],
    *,
    overwrites: Optional[dict[discord.Role | discord.Member, discord.PermissionOverwrite]] = None,
) -> discord.TextChannel:
    existing = discord.utils.find(
        lambda channel: channel.category_id == category.id and channel.name.casefold() == name.casefold(),
        guild.text_channels,
    )
    if existing is not None:
        return existing

    channel = await guild.create_text_channel(
        name,
        category=category,
        overwrites=overwrites,
        reason="Community bot server setup",
    )
    created.append(f"text channel: #{channel.name}")
    return channel


async def ensure_voice_channel(
    guild: discord.Guild,
    category: discord.CategoryChannel,
    name: str,
    created: list[str],
) -> discord.VoiceChannel:
    existing = discord.utils.find(
        lambda channel: channel.category_id == category.id and channel.name.casefold() == name.casefold(),
        guild.voice_channels,
    )
    if existing is not None:
        return existing

    channel = await guild.create_voice_channel(
        name,
        category=category,
        reason="Community bot server setup",
    )
    created.append(f"voice channel: {channel.name}")
    return channel


async def update_permission_if_needed(
    channel: discord.abc.GuildChannel,
    target: discord.Role | discord.Member,
    **permissions: Optional[bool],
) -> None:
    current = channel.overwrites_for(target)
    changed = any(getattr(current, key) is not value for key, value in permissions.items())
    if changed:
        await channel.set_permissions(
            target,
            reason="Community bot permission setup",
            **permissions,
        )


async def upsert_role_picker_message(
    channel: discord.TextChannel,
    guild_config: dict[str, Any],
) -> discord.Message:
    old_channel_id = guild_config.get("role_channel_id")
    old_message_id = guild_config.get("role_message_id")

    if old_channel_id == channel.id and old_message_id:
        try:
            message = await channel.fetch_message(int(old_message_id))
            await message.edit(embed=language_embed(), content=None, view=LanguageRoleView())
            return message
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            pass

    return await channel.send(embed=language_embed(), view=LanguageRoleView())


@app_commands.command(name="setup", description="Create or repair the server layout and language role system.")
@app_commands.describe(
    welcome_channel="Channel where new-member welcome messages should be posted",
    role_channel="Channel where the language selector should be posted",
)
@app_commands.guild_only()
@app_commands.default_permissions(administrator=True)
@app_commands.checks.has_permissions(administrator=True)
async def setup_command(
    interaction: discord.Interaction,
    welcome_channel: Optional[discord.TextChannel] = None,
    role_channel: Optional[discord.TextChannel] = None,
) -> None:
    if interaction.guild is None:
        return

    required = await require_bot_permissions(
        interaction,
        "manage_channels",
        "manage_roles",
        "send_messages",
        "embed_links",
        "view_channel",
    )
    if not required:
        return

    await interaction.response.defer(ephemeral=True, thinking=True)
    guild = interaction.guild
    created: list[str] = []

    try:
        important_category = await ensure_category(guild, IMPORTANT_CATEGORY, created)
        important_channels: dict[str, discord.TextChannel] = {}
        for channel_name in IMPORTANT_CHANNELS:
            important_channels[channel_name] = await ensure_text_channel(
                guild,
                important_category,
                channel_name,
                created,
            )

        main_category = await ensure_category(guild, MAIN_CATEGORY, created)
        for channel_name in MAIN_CHANNELS:
            await ensure_text_channel(guild, main_category, channel_name, created)

        voice_category = await ensure_category(guild, VOICE_CATEGORY, created)
        for channel_name in VOICE_CHANNELS:
            await ensure_voice_channel(guild, voice_category, channel_name, created)

        playing_category = await ensure_category(guild, PLAYING_CATEGORY, created)
        for channel_name in PLAYING_CHANNELS:
            await ensure_voice_channel(guild, playing_category, channel_name, created)

        language_category = await ensure_category(guild, LANGUAGE_CATEGORY, created)
        if guild.me is None:
            raise RuntimeError("The bot's guild member record is unavailable.")

        await update_permission_if_needed(
            language_category,
            guild.default_role,
            view_channel=False,
        )
        await update_permission_if_needed(
            language_category,
            guild.me,
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            manage_channels=True,
        )

        role_ids: dict[str, int] = {}
        language_channel_ids: dict[str, int] = {}
        unmanageable_roles: list[str] = []

        for language in LANGUAGES:
            role = find_named(guild.roles, language)
            if role is None:
                role = await guild.create_role(
                    name=language,
                    mentionable=False,
                    reason="Community bot language setup",
                )
                created.append(f"role: {language}")

            role_ids[language] = role.id
            if not role_is_manageable(guild, role):
                unmanageable_roles.append(role.name)

            channel_name = f"🗣・{language.lower()}"
            language_channel = await ensure_text_channel(
                guild,
                language_category,
                channel_name,
                created,
                overwrites={
                    guild.default_role: discord.PermissionOverwrite(view_channel=False),
                    role: discord.PermissionOverwrite(
                        view_channel=True,
                        send_messages=True,
                        read_message_history=True,
                    ),
                    guild.me: discord.PermissionOverwrite(
                        view_channel=True,
                        send_messages=True,
                        read_message_history=True,
                        manage_channels=True,
                    ),
                },
            )
            await update_permission_if_needed(
                language_channel,
                role,
                view_channel=True,
                send_messages=True,
                read_message_history=True,
            )
            language_channel_ids[language] = language_channel.id

        chosen_welcome_channel = welcome_channel or important_channels["👋・welcome"]
        chosen_role_channel = role_channel or important_channels["🤖・get-roles"]

        current_config = bot.config.guild(guild.id)
        role_message = await upsert_role_picker_message(chosen_role_channel, current_config)

        await bot.config.update_guild(
            guild.id,
            welcome_channel_id=chosen_welcome_channel.id,
            role_channel_id=chosen_role_channel.id,
            role_message_id=role_message.id,
            language_roles=role_ids,
            language_channels=language_channel_ids,
        )

    except discord.Forbidden:
        LOGGER.exception("Setup failed because Discord denied an operation")
        await interaction.followup.send(
            "Setup stopped because Discord denied an operation. Confirm my permissions and move my role above every language role.",
            ephemeral=True,
        )
        return
    except discord.HTTPException as exc:
        LOGGER.exception("Discord HTTP error during setup")
        await interaction.followup.send(f"Discord rejected part of the setup: {exc}", ephemeral=True)
        return
    except Exception:
        LOGGER.exception("Unexpected setup failure")
        await interaction.followup.send(
            "Setup failed unexpectedly. Check the bot console for the full traceback.",
            ephemeral=True,
        )
        return

    summary = (
        f"Setup complete. Welcome messages: {chosen_welcome_channel.mention}. "
        f"Language selector: {chosen_role_channel.mention}."
    )
    if created:
        summary += f" Created {len(created)} missing item(s)."
    else:
        summary += " Existing server structure was repaired and reused."

    if unmanageable_roles:
        summary += (
            " Warning: move my bot role above these language roles before members use the selector: "
            + ", ".join(sorted(set(unmanageable_roles)))
            + "."
        )

    await interaction.followup.send(summary, ephemeral=True)


@app_commands.command(name="clear", description="Delete a selected number of recent messages from this channel.")
@app_commands.describe(amount="Number of recent messages to delete, from 1 to 500")
@app_commands.guild_only()
@app_commands.default_permissions(manage_messages=True)
@app_commands.checks.has_permissions(manage_messages=True)
async def clear_command(interaction: discord.Interaction, amount: int = 100) -> None:
    if amount < 1 or amount > 500:
        await send_ephemeral(interaction, "Amount must be between 1 and 500.")
        return

    if not await require_bot_permissions(interaction, "manage_messages", "read_message_history"):
        return

    channel = interaction.channel
    if not isinstance(channel, (discord.TextChannel, discord.Thread)):
        await send_ephemeral(interaction, "This command only works in a text channel or thread.")
        return

    await interaction.response.defer(ephemeral=True, thinking=True)
    try:
        deleted = await channel.purge(
            limit=amount,
            reason=f"Requested by {interaction.user} via /clear",
        )
    except discord.Forbidden:
        await interaction.followup.send(
            "I do not have permission to delete messages here.",
            ephemeral=True,
        )
        return
    except discord.HTTPException as exc:
        await interaction.followup.send(f"Discord rejected the purge: {exc}", ephemeral=True)
        return

    await interaction.followup.send(f"Deleted {len(deleted)} message(s).", ephemeral=True)


language_group = app_commands.Group(
    name="language",
    description="Manage your language channel roles.",
    guild_only=True,
)


async def change_single_language_role(
    interaction: discord.Interaction,
    language: str,
    *,
    remove: bool,
) -> None:
    if interaction.guild is None:
        return

    member = interaction.user
    if not isinstance(member, discord.Member):
        await send_ephemeral(interaction, "I could not resolve your server membership.")
        return

    guild_config = bot.config.guild(interaction.guild.id)
    role = resolve_role(interaction.guild, language, guild_config)
    if role is None:
        await send_ephemeral(interaction, "That role is missing. Ask an administrator to run `/setup`.")
        return

    if not role_is_manageable(interaction.guild, role):
        await send_ephemeral(
            interaction,
            "I cannot manage that role. Move my bot role above the language roles.",
        )
        return

    try:
        if remove:
            await member.remove_roles(role, reason="Language role slash command")
            await send_ephemeral(interaction, f"Removed {LANGUAGES[language]} {language}.")
        else:
            await member.add_roles(role, reason="Language role slash command")
            await send_ephemeral(interaction, f"Added {LANGUAGES[language]} {language}.")
    except discord.Forbidden:
        await send_ephemeral(interaction, "I do not have permission to manage that role.")
    except discord.HTTPException as exc:
        await send_ephemeral(interaction, f"Discord rejected the role update: {exc}")


@language_group.command(name="add", description="Add one language role to yourself.")
@app_commands.describe(language="Language role to add")
@app_commands.choices(language=LANGUAGE_CHOICES)
async def language_add(
    interaction: discord.Interaction,
    language: app_commands.Choice[str],
) -> None:
    await change_single_language_role(interaction, language.value, remove=False)


@language_group.command(name="remove", description="Remove one language role from yourself.")
@app_commands.describe(language="Language role to remove")
@app_commands.choices(language=LANGUAGE_CHOICES)
async def language_remove(
    interaction: discord.Interaction,
    language: app_commands.Choice[str],
) -> None:
    await change_single_language_role(interaction, language.value, remove=True)


@language_group.command(name="clear", description="Remove all language roles from yourself.")
async def language_clear(interaction: discord.Interaction) -> None:
    if interaction.guild is None or not isinstance(interaction.user, discord.Member):
        return

    guild_config = bot.config.guild(interaction.guild.id)
    roles = [
        role
        for language in LANGUAGES
        if (role := resolve_role(interaction.guild, language, guild_config)) is not None
        and role in interaction.user.roles
    ]

    if not roles:
        await send_ephemeral(interaction, "You do not currently have any language roles.")
        return

    unmanaged = [role.name for role in roles if not role_is_manageable(interaction.guild, role)]
    if unmanaged:
        await send_ephemeral(
            interaction,
            "I cannot remove these roles because they are above my highest role: "
            + ", ".join(unmanaged),
        )
        return

    try:
        await interaction.user.remove_roles(*roles, reason="Cleared language roles")
    except discord.Forbidden:
        await send_ephemeral(interaction, "I do not have permission to remove those roles.")
        return
    except discord.HTTPException as exc:
        await send_ephemeral(interaction, f"Discord rejected the role update: {exc}")
        return

    await send_ephemeral(interaction, "Removed all of your language roles.")


@app_commands.command(
    name="setup_translations",
    description="Generate a manual checklist for configuring a third-party translation bot.",
)
@app_commands.guild_only()
@app_commands.default_permissions(administrator=True)
@app_commands.checks.has_permissions(administrator=True)
async def setup_translations_command(interaction: discord.Interaction) -> None:
    if interaction.guild is None:
        return

    guild_config = bot.config.guild(interaction.guild.id)
    channel_ids = guild_config.get("language_channels", {})
    if not isinstance(channel_ids, dict) or not channel_ids:
        await send_ephemeral(interaction, "Run `/setup` before generating translation instructions.")
        return

    instructions = [
        "Discord bots cannot execute another bot's slash commands by posting command text. "
        "Run the translation bot's command manually in each channel:",
        "",
    ]
    for language in LANGUAGES:
        channel_id = channel_ids.get(language)
        channel = interaction.guild.get_channel(int(channel_id)) if channel_id else None
        if isinstance(channel, discord.TextChannel):
            instructions.append(
                f"• {channel.mention}: run `/set_dedicated_lang` and select `{language.lower()}`"
            )

    await send_ephemeral(interaction, "\n".join(instructions))


@app_commands.command(name="help", description="Show the bot's available slash commands.")
@app_commands.guild_only()
async def help_command(interaction: discord.Interaction) -> None:
    embed = discord.Embed(
        title="Community bot commands",
        description="All commands use Discord application commands; no message prefix is required.",
        colour=discord.Colour.blurple(),
    )
    embed.add_field(
        name="Server administration",
        value=(
            "`/setup` — create or repair the server layout and role menu\n"
            "`/clear` — remove recent messages\n"
            "`/setup_translations` — generate the manual translation-bot checklist"
        ),
        inline=False,
    )
    embed.add_field(
        name="Member commands",
        value=(
            "`/language add` — add a language role\n"
            "`/language remove` — remove a language role\n"
            "`/language clear` — remove all language roles\n"
            "`/status` — show connection and setup status"
        ),
        inline=False,
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)


@app_commands.command(name="status", description="Show the bot's connection and setup status.")
@app_commands.guild_only()
async def status_command(interaction: discord.Interaction) -> None:
    if interaction.guild is None:
        return

    guild_config = bot.config.guild(interaction.guild.id)
    welcome_channel = interaction.guild.get_channel(int(guild_config.get("welcome_channel_id", 0)))
    role_channel = interaction.guild.get_channel(int(guild_config.get("role_channel_id", 0)))
    configured_roles = guild_config.get("language_roles", {})
    role_count = len(configured_roles) if isinstance(configured_roles, dict) else 0

    embed = discord.Embed(title="Bot status", colour=discord.Colour.green())
    embed.add_field(name="Latency", value=f"{round(bot.latency * 1000)} ms")
    embed.add_field(name="discord.py", value=discord.__version__)
    embed.add_field(name="Language roles", value=f"{role_count}/{len(LANGUAGES)} configured")
    embed.add_field(
        name="Welcome channel",
        value=welcome_channel.mention if isinstance(welcome_channel, discord.TextChannel) else "Not configured",
        inline=False,
    )
    embed.add_field(
        name="Role channel",
        value=role_channel.mention if isinstance(role_channel, discord.TextChannel) else "Not configured",
        inline=False,
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)


bot.tree.add_command(setup_command)
bot.tree.add_command(clear_command)
bot.tree.add_command(language_group)
bot.tree.add_command(setup_translations_command)
bot.tree.add_command(help_command)
bot.tree.add_command(status_command)


@bot.event
async def on_ready() -> None:
    if len(bot.guilds) == 1:
        await bot.config.migrate_legacy(bot.guilds[0].id)

    if bot.user is not None:
        LOGGER.info("Logged in as %s (%s)", bot.user, bot.user.id)


@bot.event
async def on_member_join(member: discord.Member) -> None:
    guild_config = bot.config.guild(member.guild.id)
    welcome_channel_id = guild_config.get("welcome_channel_id")
    role_channel_id = guild_config.get("role_channel_id")

    if not welcome_channel_id:
        return

    welcome_channel = member.guild.get_channel(int(welcome_channel_id))
    if not isinstance(welcome_channel, discord.TextChannel):
        return

    role_channel = member.guild.get_channel(int(role_channel_id)) if role_channel_id else None
    role_text = (
        f" Choose your language roles in {role_channel.mention}."
        if isinstance(role_channel, discord.TextChannel)
        else " Ask an administrator where to choose your language roles."
    )

    try:
        await welcome_channel.send(f"👋 Welcome {member.mention}!{role_text}")
    except discord.HTTPException:
        LOGGER.exception("Could not send welcome message in guild %s", member.guild.id)


@bot.tree.error
async def on_app_command_error(
    interaction: discord.Interaction,
    error: app_commands.AppCommandError,
) -> None:
    if isinstance(error, app_commands.MissingPermissions):
        await send_ephemeral(
            interaction,
            "You do not have permission to use that command. Missing: "
            + ", ".join(error.missing_permissions),
        )
        return

    if isinstance(error, app_commands.BotMissingPermissions):
        await send_ephemeral(
            interaction,
            "I am missing required permissions: " + ", ".join(error.missing_permissions),
        )
        return

    original = error.original if isinstance(error, app_commands.CommandInvokeError) else error
    LOGGER.exception("Unhandled application command error", exc_info=original)
    await send_ephemeral(
        interaction,
        "That command failed unexpectedly. Check the bot console for the traceback.",
    )


def main() -> None:
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise RuntimeError(
            "DISCORD_TOKEN is missing. Copy .env.example to .env and place your bot token there."
        )

    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    bot.run(token, log_handler=None)


if __name__ == "__main__":
    main()
