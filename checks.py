import discord
from discord import app_commands

def is_moderator():
    async def predicate(interaction: discord.Interaction):
        perms = interaction.user.guild_permissions
        return (
            perms.ban_members or
            perms.kick_members or
            perms.moderate_members or
            perms.manage_guild or
            perms.administrator
        )
    return app_commands.check(predicate)
