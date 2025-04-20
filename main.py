import discord
import os
import asyncio
import json
from discord.ext import commands

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.guilds = True
intents.reactions = True

bot = commands.Bot(command_prefix="!", intents=intents)

if os.path.exists("config.json"):
    with open("config.json", "r") as f:
        config = json.load(f)
else:
    config = {}
def save_config():
    with open("config.json", "w") as f:
        json.dump(config, f, indent=4)

language_flag_map = {
    "English": "🇬🇧",
    "Mandarin": "🇨🇳",
    "Hindi": "🇮🇳",
    "Spanish": "🇪🇸",
    "French": "🇫🇷",
    "Arabic": "🇸🇦",
    "Bengali": "🇧🇩",
    "Russian": "🇷🇺",
    "Portuguese": "🇵🇹",
    "Urdu": "🇵🇰"
}


@bot.event
async def on_raw_reaction_add(payload):

    if payload.user_id == bot.user.id:
        return


    if payload.message_id != config.get("reaction_message_id"):
        return

    guild = bot.get_guild(payload.guild_id)
    if not guild:
        return

    emoji = str(payload.emoji)


    language = None
    for lang, flag in language_flag_map.items():
        if flag == emoji:
            language = lang
            break

    if not language:
        print(f"⚠️ No language found for emoji {emoji}")
        return


    role = discord.utils.get(guild.roles, name=language)
    if not role:
        print(f"⚠️ Could not find the role for language {language}")
        return

    member = guild.get_member(payload.user_id)
    if not member:
        print(f"⚠️ Could not find the member with ID {payload.user_id}")
        return

    try:
        await member.add_roles(role)
        print(f"🎉 {member.name} has been successfully assigned the {role.name} role.")


        language_channel_name = f"🗣・{language}"
        language_channel = discord.utils.get(guild.text_channels, name=language_channel_name.lower())

        if language_channel:
            await language_channel.set_permissions(member, read_messages=True)
            print(f"🔐 {member.name} has been granted access to {language_channel_name}.")
    except discord.Forbidden:
        print(f"⚠️ Failed to assign the {role.name} role to {member.name}: Bot does not have permission.")
    except discord.HTTPException as e:
        print(f"⚠️ Failed to assign the {role.name} role to {member.name}: {e}")


@commands.has_permissions(administrator=True)
@bot.command()
async def setup(ctx, welcome_channel: discord.TextChannel):
    await ctx.message.delete()  # delete the command itself
    guild = ctx.guild
    config["welcome_channel_id"] = welcome_channel.id
    config["language_roles"] = {}

    # Create Important category and channels
    important_category_name = "💳 | ==== Important ==== | 💳"
    important_category = discord.utils.get(guild.categories, name=important_category_name)
    if not important_category:
        important_category = await guild.create_category(name=important_category_name)
        print(f"📣 Created category: {important_category_name}")

    important_channels = ["👋・welcome", "📜・rules", "📣・announcements", "📦・resources","🤖・get-roles" ]
    for channel_name in important_channels:
        channel = discord.utils.get(guild.text_channels, name=channel_name.lower(), category=important_category)
        if not channel:
            channel = await guild.create_text_channel(channel_name, category=important_category)
            print(f"📣 Created channel: #{channel_name} in {important_category_name}")


    main_category_name = "👥 | ====== Thought Chambers ====== | 👥"
    main_category = discord.utils.get(guild.categories, name=main_category_name)
    if not main_category:
        main_category = await guild.create_category(name=main_category_name)
        print(f"📣 Created category: {main_category_name}")

    main_channels = ["💬・general", "👥・debate", "🧪・science", "✝️・religion", "🏺・history", "🚧・projects", "📬・off-topic"]
    for channel_name in main_channels:
        channel = discord.utils.get(guild.text_channels, name=channel_name.lower(), category=main_category)
        if not channel:
            channel = await guild.create_text_channel(channel_name, category=main_category)
            print(f"📣 Created channel: #{channel_name} in {main_category_name}")


    voice_category_name = "🔊 | ====== Voice ====== | 🔊"
    voice_category = discord.utils.get(guild.categories, name=voice_category_name)
    if not voice_category:
        voice_category = await guild.create_category(name=voice_category_name)
        print(f"📣 Created category: {voice_category_name}")

    voice_channels = ["🔊・Lounge", "🎵・Music", "📅・Meeting", "🎮・Gaming", "💤・AFK"]
    for channel_name in voice_channels:
        channel = discord.utils.get(guild.voice_channels, name=channel_name, category=voice_category)
        if not channel:
            channel = await guild.create_voice_channel(channel_name, category=voice_category)
            print(f"📣 Created channel: #{channel_name} in {voice_category_name}")


    playing_category_name = "🌀 | === Playing Rooms === | 🌀"
    playing_category = discord.utils.get(guild.categories, name=playing_category_name)
    if not playing_category:
        playing_category = await guild.create_category(name=playing_category_name)
        print(f"📣 Created category: {playing_category_name}")

    playing_channels = ["🌀・Duos", "🌀・Trios", "🌀・Squads"]
    for channel_name in playing_channels:
        channel = discord.utils.get(guild.voice_channels, name=channel_name, category=playing_category)
        if not channel:
            channel = await guild.create_voice_channel(channel_name, category=playing_category)
            print(f"📣 Created channel: #{channel_name} in {playing_category_name}")


    language_category_name = "🌍 | Language Zones | 🌍"
    language_category = discord.utils.get(guild.categories, name=language_category_name)
    if not language_category:
        language_category = await guild.create_category(name=language_category_name)
        print(f"📣 Created category: {language_category_name}")

    for language, flag in language_flag_map.items():

        role = discord.utils.get(guild.roles, name=language)
        if not role:
            role = await guild.create_role(name=language)
            print(f"📣 Created role: {language}")


        channel_name = f"🗣・{language}"
        channel = discord.utils.get(guild.text_channels, name=channel_name.lower(), category=language_category)
        if not channel:
            channel = await guild.create_text_channel(channel_name, category=language_category)
            print(f"📣 Created channel: #{channel_name} in {language_category_name}")


        await channel.set_permissions(guild.default_role, read_messages=False)
        await channel.set_permissions(role, read_messages=True)

    #welcome message
    multilingual_message = (
        "👋 **Welcome! Pick your language by selecting your flag:**\n\n"
        "🇬🇧 English: Pick your language by selecting your flag\n"
        "🇨🇳 中文: 通过选择你的国旗来选择语言\n"
        "🇮🇳 हिंदी: अपने ध्वज का चयन करके अपनी भाषा चुनें\n"
        "🇪🇸 Español: Selecciona tu idioma eligiendo tu bandera\n"
        "🇫🇷 Français: Choisissez votre langue en sélectionnant votre drapeau\n"
        "🇸🇦 العربية: اختر لغتك من خلال اختيار علمك\n"
        "🇧🇩 বাংলা: আপনার পতাকা নির্বাচন করে আপনার ভাষা চয়ন করুন\n"
        "🇷🇺 Русский: Выберите язык, нажав на свой флаг\n"
        "🇵🇹 Português: Escolha seu idioma selecionando sua bandeira\n"
        "🇵🇰 اردو: اپنے پرچم کو منتخب کرکے اپنی زبان منتخب کریں"
    )

    msg = await welcome_channel.send(multilingual_message)

    for emoji in language_flag_map.values():
        await msg.add_reaction(emoji)

    config["reaction_message_id"] = msg.id
    save_config()

    await ctx.send("-# Made By HelloGoodByeLetsNot. [Learn More](<https://etsradios.blogspot.com/>)")


@commands.has_permissions(administrator=True)
@bot.command()
async def clear(ctx):
    """Clears all messages in the current channel (Admin only)."""
    await ctx.message.delete()  # delete the command itself
    await ctx.send("🧹 Clearing messages...", delete_after=3)

    try:
        deleted = await ctx.channel.purge(limit=None)
        confirmation = await ctx.send(f"✅ Cleared {len(deleted)} messages.")
        await asyncio.sleep(5)
        await confirmation.delete()
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to delete messages here.", delete_after=5)
    except Exception as e:
        await ctx.send(f"⚠️ Something went wrong: {e}", delete_after=5)


@commands.has_permissions(administrator=True)
@bot.command()
async def setup_translations(ctx):
    """Set up translations for all language channels"""
    # Delete the command message
    try:
        await ctx.message.delete()
    except:
        pass

    # Get the language category
    guild = ctx.guild
    language_category_name = "🌍 | Language Channels | 🌍"
    language_category = discord.utils.get(guild.categories, name=language_category_name)

    if not language_category:
        error_msg = await ctx.send(f"❌ Category '{language_category_name}' not found.")
        await asyncio.sleep(10)
        await error_msg.delete()
        return

    status_msg = await ctx.send(f"🔄 Setting up translations for language channels...")

    # Process each language channel
    success_count = 0
    for channel in language_category.text_channels:
        try:
            # Extract language name from channel (format: "🗣・Language")
            language_name = channel.name.split('・')[1] if '・' in channel.name else channel.name

            # Send the command in each channel
            await channel.send(f"/set_dedicated_lang language {language_name.lower()}")

            # Wait a moment between commands to avoid rate limiting
            await asyncio.sleep(2)
            success_count += 1

        except Exception as e:
            print(f"⚠️ Error setting up translation for {channel.name}: {e}")

    # Update status message
    await status_msg.edit(content=f"✅ Set up translations for {success_count} language channels.")
    await asyncio.sleep(10)
    await status_msg.delete()

@bot.event
async def on_member_join(member):
    welcome_channel = bot.get_channel(config.get("welcome_channel_id"))
    if welcome_channel:
        await welcome_channel.send(f"👋 Welcome {member.mention}! Please pick your language above by clicking a flag.")


bot.run("TOKEN")
