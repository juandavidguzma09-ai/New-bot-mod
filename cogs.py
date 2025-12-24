import discord
from discord.ext import commands
from discord import app_commands
from utils.checks import is_moderator

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ban")
    @is_moderator()
    async def ban(self, interaction, user: discord.Member, reason: str="No reason"):
        if interaction.user.top_role <= user.top_role:
            return await interaction.response.send_message(
                "❌ No puedes moderar a alguien con tu mismo o mayor rol",
                ephemeral=True
            )
        await user.ban(reason=reason)
        await interaction.response.send_message("🔨 Ban ejecutado")

    @app_commands.command(name="kick")
    @is_moderator()
    async def kick(self, interaction, user: discord.Member, reason: str="No reason"):
        await user.kick(reason=reason)
        await interaction.response.send_message("👢 Kick ejecutado")

    @app_commands.command(name="timeout")
    @is_moderator()
    async def timeout(self, interaction, user: discord.Member, minutes: int):
        await user.timeout(
            discord.utils.utcnow() + discord.timedelta(minutes=minutes)
        )
        await interaction.response.send_message("🔇 Timeout aplicado")

    @app_commands.command(name="untimeout")
    @is_moderator()
    async def untimeout(self, interaction, user: discord.Member):
        await user.timeout(None)
        await interaction.response.send_message("🔊 Timeout removido")

async def setup(bot):
    await bot.add_cog(Moderation(bot))
