import discord
from discord.ext import commands
from discord import app_commands
from utils.checks import is_moderator

class Lockdown(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="lock")
    @is_moderator()
    async def lock(self, interaction):
        for ch in interaction.guild.text_channels:
            await ch.set_permissions(
                interaction.guild.default_role,
                send_messages=False
            )
        await interaction.response.send_message("🔒 Servidor bloqueado")

    @app_commands.command(name="unlock")
    @is_moderator()
    async def unlock(self, interaction):
        for ch in interaction.guild.text_channels:
            await ch.set_permissions(
                interaction.guild.default_role,
                send_messages=True
            )
        await interaction.response.send_message("🔓 Servidor desbloqueado")

async def setup(bot):
    await bot.add_cog(Lockdown(bot))
