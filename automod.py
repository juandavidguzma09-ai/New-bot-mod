import discord, time
from discord.ext import commands
from config import SPAM_LIMIT, SPAM_TIME, LINK_WHITELIST

class AutoMod(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cache = {}

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        uid = message.author.id
        now = time.time()

        self.cache.setdefault(uid, []).append(now)
        self.cache[uid] = [t for t in self.cache[uid] if now - t < SPAM_TIME]

        if len(self.cache[uid]) > SPAM_LIMIT:
            await message.delete()
            await message.author.timeout(
                discord.utils.utcnow() + discord.timedelta(minutes=5)
            )

        if message.mention_everyone:
            await message.delete()

        if "http" in message.content:
            if not any(w in message.content for w in LINK_WHITELIST):
                await message.delete()

async def setup(bot):
    await bot.add_cog(AutoMod(bot))
