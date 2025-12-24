import discord
from discord.ext import commands
from discord import app_commands
import datetime

class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def embed_success(self, title, desc):
        return discord.Embed(title=title, description=desc, color=0x50FA7B)

    def embed_error(self, title, desc):
        return discord.Embed(title=title, description=desc, color=0xFF5555)

    @commands.hybrid_command(name="setprefix", description="Cambia el prefijo del bot.")
    @commands.has_permissions(administrator=True)
    async def setprefix(self, ctx, nuevo_prefix: str):
        await self.bot.db.execute("INSERT OR REPLACE INTO guilds (guild_id, prefix) VALUES (?, ?)", (ctx.guild.id, nuevo_prefix))
        await self.bot.db.commit()
        await ctx.send(embed=self.embed_success("Configuración", f"Prefijo actualizado a: `{nuevo_prefix}`"))

    @commands.hybrid_command(name="kick", description="Expulsa a un usuario.")
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, miembro: discord.Member, *, razon: str = "Sin razón"):
        if miembro.top_role >= ctx.author.top_role:
            return await ctx.send(embed=self.embed_error("Error", "No puedes expulsar a alguien con rango superior o igual."))
        
        await miembro.kick(reason=razon)
        await ctx.send(embed=self.embed_success("Usuario Expulsado", f"👤 **{miembro}**\n📝 Razón: {razon}"))

    @commands.hybrid_command(name="ban", description="Banea a un usuario.")
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, miembro: discord.Member, *, razon: str = "Sin razón"):
        await miembro.ban(reason=razon)
        await ctx.send(embed=self.embed_success("Usuario Baneado", f"🔨 **{miembro}** fue golpeado por el martillo.\n📝 Razón: {razon}"))

    @commands.hybrid_command(name="purge", description="Elimina mensajes masivamente.")
    @commands.has_permissions(manage_messages=True)
    async def purge(self, ctx, cantidad: int):
        if cantidad > 100: cantidad = 100
        await ctx.defer(ephemeral=True)
        deleted = await ctx.channel.purge(limit=cantidad)
        await ctx.send(f"🧹 Se han eliminado {len(deleted)} mensajes.", ephemeral=True)

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if not message.guild or message.author.bot: return
        cursor = await self.bot.db.execute("SELECT log_channel FROM guilds WHERE guild_id = ?", (message.guild.id,))
        result = await cursor.fetchone()
        
        if result and result[0]:
            channel = message.guild.get_channel(result[0])
            if channel:
                embed = discord.Embed(title="🗑️ Mensaje Borrado", color=0xFF5555, timestamp=datetime.datetime.now())
                embed.add_field(name="Autor", value=message.author.mention, inline=True)
                embed.add_field(name="Canal", value=message.channel.mention, inline=True)
                embed.add_field(name="Contenido", value=message.content or "[Imagen/Archivo]", inline=False)
                await channel.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Admin(bot))
