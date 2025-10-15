# -*- coding: utf-8 -*-
"""
Discord Bot med auto-roll, anti-raid (lockdown), timmeddelanden och slash-kommandon
Optimerad för 24/7-drift på Render med UptimeRobot
"""

import discord
from discord.ext import commands, tasks
from discord import app_commands
import os
import random
from datetime import datetime, timedelta
from collections import defaultdict

# ===== Starta keep-alive server =====
from keep_alive import keep_alive
keep_alive()

# ===== Miljövariabler =====
TOKEN = os.getenv('DISCORD_BOT_TOKEN')  # Ange token som miljövariabel på Render

# ===== Intents =====
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix='!', intents=intents)

# ===== KONFIGURATION =====
AUTO_ROLE_NAME = "Member"
ANTI_RAID_TIME_WINDOW = 60
ANTI_RAID_THRESHOLD = 5
HOURLY_MESSAGE_CHANNEL_NAME = "general-💬"
HOURLY_MESSAGE = "SKICKA IN I exposé-📸"
HOURLY_MESSAGE_INTERVAL_HOURS = 2  # Ändra här för att skicka meddelande varje X timmar

# ===== ANTI-RAID =====
join_times = defaultdict(list)

def check_raid(guild_id):
    now = datetime.now()
    join_times[guild_id] = [t for t in join_times[guild_id] if now - t < timedelta(seconds=ANTI_RAID_TIME_WINDOW)]
    return len(join_times[guild_id]) >= ANTI_RAID_THRESHOLD

# ===== EVENTS =====
@bot.event
async def on_ready():
    print(f'✅ Bot inloggad som {bot.user.name} (ID: {bot.user.id})')
    try:
        synced = await bot.tree.sync()
        print(f'✅ Synkroniserade {len(synced)} slash-kommandon')
    except Exception as e:
        print(f'❌ Fel vid synkronisering: {e}')

    if not hourly_message.is_running():
        hourly_message.start()
        print('✅ Timmeddelanden startade')

@bot.event
async def on_member_join(member):
    guild = member.guild

    # ===== AUTO-ROLL =====
    role = discord.utils.get(guild.roles, name=AUTO_ROLE_NAME)
    if role:
        try:
            await member.add_roles(role)
            print(f'✅ Gav rollen "{AUTO_ROLE_NAME}" till {member.name}')
        except:
            print(f'❌ Kunde inte ge rollen till {member.name}')

    # ===== ANTI-RAID =====
    join_times[guild.id].append(datetime.now())
    if check_raid(guild.id):
        # Skicka raid-varning
        alert_channel = discord.utils.get(guild.text_channels, name="admin") or guild.text_channels[0]
        if alert_channel:
            embed = discord.Embed(
                title="🚨 RAID VARNING 🚨",
                description=f"**{ANTI_RAID_THRESHOLD}+ användare** har joinat inom {ANTI_RAID_TIME_WINDOW} sekunder!",
                color=discord.Color.red(),
                timestamp=datetime.now()
            )
            embed.add_field(name="Senaste medlemmen", value=f"{member.mention} ({member.name})", inline=False)
            embed.set_footer(text="Anti-Raid System")
            await alert_channel.send(embed=embed)
        
        # ===== LOCKDOWN: sätt alla textkanaler read-only =====
        for channel in guild.text_channels:
            try:
                await channel.set_permissions(guild.default_role, send_messages=False)
            except Exception as e:
                print(f"❌ Kunde inte låsa #{channel.name}: {e}")
        
        print(f'⚠️ Raid upptäckt! Alla textkanaler låsta.')

# ===== TIMMEDDELANDEN =====
@tasks.loop(hours=HOURLY_MESSAGE_INTERVAL_HOURS)
async def hourly_message():
    for guild in bot.guilds:
        channel = discord.utils.get(guild.text_channels, name=HOURLY_MESSAGE_CHANNEL_NAME)
        if channel:
            try:
                await channel.send(HOURLY_MESSAGE)
                print(f'✅ Skickade timmeddelande till #{channel.name} i {guild.name}')
            except:
                print(f'❌ Kunde inte skicka timmeddelande i #{channel.name}')

@hourly_message.before_loop
async def before_hourly_message():
    await bot.wait_until_ready()

# ===== SLASH-KOMMANDON =====
@bot.tree.command(name="hej", description="Säger hej till dig!")
async def hej(interaction: discord.Interaction):
    await interaction.response.send_message(f"👋 Hej {interaction.user.mention}! Trevligt att träffas!")

@bot.tree.command(name="ping", description="Visar botens latens")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"🏓 Pong! Latens: **{round(bot.latency*1000)}ms**")

@bot.tree.command(name="dice", description="Kastar en tärning (1-6)")
async def dice(interaction: discord.Interaction):
    result = random.randint(1,6)
    dice_emoji = ["","⚀","⚁","⚂","⚃","⚄","⚅"]
    await interaction.response.send_message(f"🎲 {interaction.user.mention} kastade tärningen och fick: **{result}** {dice_emoji[result]}")

@bot.tree.command(name="coinflip", description="Singlar slant")
async def coinflip(interaction: discord.Interaction):
    result = random.choice(["Krona","Klave"])
    emoji = "🪙" if result=="Krona" else "💿"
    await interaction.response.send_message(f"{emoji} {interaction.user.mention} singlade slant och fick: **{result}**!")

@bot.tree.command(name="joke", description="Berättar ett skämt")
async def joke(interaction: discord.Interaction):
    jokes = [
        "Varför kan inte cyklar stå själva? För att de är två-trötta! 🚴",
        "Vad säger en nolla till en åtta? Snyggt bälte! 👔",
        "Varför gick tomaten röd? Den såg salladdressingen! 🍅",
        "Vad är en pirats favoritbokstav? Rrrrr! 🏴‍☠️",
        "Hur får man en vävare att skratta? Berätta en vävande historia! 🕷️"
    ]
    await interaction.response.send_message(f"😄 Skämt:\n{random.choice(jokes)}")

# ===== MODERERINGSKOMMANDON =====
@bot.tree.command(name="kick", description="Sparkar en användare från servern")
@app_commands.checks.has_permissions(kick_members=True)
async def kick(interaction: discord.Interaction, member: discord.Member, reason: str = "Ingen anledning angiven"):
    await member.kick(reason=reason)
    await interaction.response.send_message(f"👢 {member.mention} har sparkats. Anledning: {reason}")

@bot.tree.command(name="ban", description="Bannar en användare från servern")
@app_commands.checks.has_permissions(ban_members=True)
async def ban(interaction: discord.Interaction, member: discord.Member, reason: str = "Ingen anledning angiven"):
    await member.ban(reason=reason)
    await interaction.response.send_message(f"⛔ {member.mention} har blivit bannad. Anledning: {reason}")

@bot.tree.command(name="unban", description="Häver bann av en användare")
@app_commands.checks.has_permissions(ban_members=True)
async def unban(interaction: discord.Interaction, user_id: str):
    user = await bot.fetch_user(user_id)
    await interaction.guild.unban(user)
    await interaction.response.send_message(f"✅ {user.name} har blivit unbannad.")

@bot.tree.command(name="clear", description="Rensar meddelanden i en kanal")
@app_commands.checks.has_permissions(manage_messages=True)
async def clear(interaction: discord.Interaction, amount: int):
    await interaction.channel.purge(limit=amount)
    await interaction.response.send_message(f"🧹 Rensade {amount} meddelanden!", ephemeral=True)

@bot.tree.command(name="lock", description="Låser kanalen (endast admins kan skriva)")
@app_commands.checks.has_permissions(manage_channels=True)
async def lock(interaction: discord.Interaction):
    await interaction.channel.set_permissions(interaction.guild.default_role, send_messages=False)
    await interaction.response.send_message(f"🔒 Kanalen {interaction.channel.mention} är nu låst!")

@bot.tree.command(name="unlock", description="Låser upp kanalen")
@app_commands.checks.has_permissions(manage_channels=True)
async def unlock(interaction: discord.Interaction):
    await interaction.channel.set_permissions(interaction.guild.default_role, send_messages=True)
    await interaction.response.send_message(f"🔓 Kanalen {interaction.channel.mention} är nu upplåst!")

@bot.tree.command(name="warn", description="Varnar en användare")
@app_commands.checks.has_permissions(manage_messages=True)
async def warn(interaction: discord.Interaction, member: discord.Member, reason: str = "Ingen anledning angiven"):
    await interaction.response.send_message(f"⚠️ {member.mention} har varnats. Anledning: {reason}")
    try:
        await member.send(f"⚠️ Du har fått en varning i **{interaction.guild.name}**. Anledning: {reason}")
    except:
        pass

# ===== INFORMATIONS-KOMMANDON =====
@bot.tree.command(name="userinfo", description="Visar info om en användare")
async def userinfo(interaction: discord.Interaction, member: discord.Member = None):
    member = member or interaction.user
    embed = discord.Embed(title=f"👤 Info om {member}", color=discord.Color.blue(), timestamp=datetime.now())
    embed.add_field(name="ID", value=member.id, inline=True)
    embed.add_field(name="Roller", value=", ".join([r.name for r in member.roles if r != interaction.guild.default_role]), inline=False)
    embed.add_field(name="Joined", value=member.joined_at.strftime("%Y-%m-%d %H:%M:%S"), inline=True)
    embed.add_field(name="Konto skapat", value=member.created_at.strftime("%Y-%m-%d %H:%M:%S"), inline=True)
    embed.set_thumbnail(url=member.display_avatar.url)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="serverinfo", description="Visar info om servern")
async def serverinfo(interaction: discord.Interaction):
    guild = interaction.guild
    embed = discord.Embed(title=f"🏰 Serverinfo: {guild.name}", color=discord.Color.green(), timestamp=datetime.now())
    embed.add_field(name="Medlemmar", value=guild.member_count)
    embed.add_field(name="Textkanaler", value=len(guild.text_channels))
    embed.add_field(name="Röstkanaler", value=len(guild.voice_channels))
    embed.add_field(name="Roller", value=len(guild.roles))
    embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="avatar", description="Visar användarens profilbild")
async def avatar(interaction: discord.Interaction, member: discord.Member = None):
    member = member or interaction.user
    embed = discord.Embed(title=f"🖼️ {member.name}'s avatar", color=discord.Color.purple())
    embed.set_image(url=member.display_avatar.url)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="uptime", description="Visar hur länge boten har varit igång")
async def uptime(interaction: discord.Interaction):
    delta = datetime.now() - bot.start_time
    hours, remainder = divmod(int(delta.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)
    await interaction.response.send_message(f"⏱️ Boten har varit igång i **{hours}h {minutes}m {seconds}s**.")

# ===== STARTTID =====
bot.start_time = datetime.now()

# ===== STARTA BOTEN =====
if __name__ == "__main__":
    if not TOKEN:
        print("❌ ERROR: DISCORD_BOT_TOKEN hittades inte i miljövariablerna!")
    else:
        print("🚀 Startar Discord bot...")
        bot.run(TOKEN)




