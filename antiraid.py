import discord, time
from discord.ext import commands
from config import ANTI_RAID_JOIN_LIMIT, ANTI_RAID_TIME

class AntiRaid(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.joins = []

    @commands.Cog.listener()
    async def on_member_join(self, member):
        now = time.time()
        self.joins.append(now)
        self.joins = [t for t in self.joins if now - t < ANTI_RAID_TIME]

        if len(self.joins) >= ANTI_RAID_JOIN_LIMIT:
            for ch in member.guild.text_channels:
                await ch.set_permissions(
                    member.guild.default_role,
                    send_messages=False
                )

            if member.guild.system_channel:
                await member.guild.system_channel.send(
                    "🚨 **ANTI-RAID ACTIVADO AUTOMÁTICAMENTE**"
                )

async def setup(bot):
    await bot.add_cog(AntiRaid(bot))
