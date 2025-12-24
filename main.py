import discord
from discord.ext import commands
from config import TOKEN

intents = discord.Intents.all()

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"[AEGISX] ONLINE | {bot.user}")

COGS = [
    "cogs.moderation",
    "cogs.antiraid",
    "cogs.automod",
    "cogs.lockdown",
    "cogs.roles",
    "cogs.logs",
    "cogs.utilities",
    "cogs.admin"
]

for cog in COGS:
    bot.load_extension(cog)

bot.run(TOKEN)
