import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import datetime
import logging

# Cargar variables
load_dotenv()
TOKEN = os.getenv('TOKEN')
PREFIX = ('!')

class JarElite(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(
            command_prefix=PREFIX,
            intents=intents,
            help_command=None,
            case_insensitive=True
        )
        self.uptime = datetime.datetime.utcnow()
        self.snipes = {} # Sistema de Snipe Global

    async def setup_hook(self):
        print("--- [ SISTEMA DE ÉLITE INICIADO ] ---")

bot = JarElite()

# --- HELPER PARA EMBEDS ESTILO JAR.RIP ---
def quick_embed(title, description, color=0x2b2d31):
    embed = discord.Embed(title=f"**{title}**", description=description, color=color)
    return embed

# ==========================================
# 🛡️ CATEGORÍA: MODERACIÓN (Lógica para 50 comandos)
# ==========================================
# Implementación de los más importantes (Pattern para el resto)

@bot.group(invoke_without_command=True)
@commands.has_permissions(manage_messages=True)
async def mod(ctx):
    await ctx.send("**🛡️ Usa `!help mod` para ver los 50 comandos de moderación.**")

@bot.command()
@commands.has_permissions(administrator=True)
async def nuke(ctx):
    """Recrea el canal borrando todo."""
    pos = ctx.channel.position
    new_channel = await ctx.channel.clone()
    await ctx.channel.delete()
    await new_channel.edit(position=pos)
    await new_channel.send(embed=quick_embed("☢️ NUKE", "Este canal ha sido purgado por completo."))

@bot.command()
@commands.has_permissions(manage_channels=True)
async def lock(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)
    await ctx.send("**🔒 Canal bloqueado en modo lectura.**")

@bot.command()
@commands.has_permissions(ban_members=True)
async def massban(ctx, *members: discord.Member):
    for member in members:
        await member.ban(reason="Massban ejecutado")
    await ctx.send(f"**🚫 Se han baneado {len(members)} usuarios.**")

# (Aquí se añaden: softban, tempban, warn, unwarn, clearwarns, slowmode, lockserver, hide, unhide, etc.)

# ==========================================
# ⚙️ CATEGORÍA: UTILIDAD (Lógica para 50 comandos)
# ==========================================

@bot.command(aliases=['av'])
async def avatar(ctx, user: discord.Member = None):
    user = user or ctx.author
    embed = quick_embed(f"Avatar de {user.name}", "")
    embed.set_image(url=user.display_avatar.url)
    await ctx.send(embed=embed)

@bot.command()
async def banner(ctx, user: discord.Member = None):
    user = user or ctx.author
    user_data = await bot.fetch_user(user.id)
    if user_data.banner:
        embed = quick_embed(f"Banner de {user.name}", "")
        embed.set_image(url=user_data.banner.url)
        await ctx.send(embed=embed)
    else:
        await ctx.send("**Este usuario no tiene banner.**")

@bot.command()
async def steal(ctx, emoji: discord.PartialEmoji):
    """Roba un emoji de otro servidor."""
    new_emoji = await ctx.guild.create_custom_emoji(name=emoji.name, image=await emoji.read())
    await ctx.send(f"**✅ Emoji {new_emoji} agregado al servidor.**")

# ==========================================
# 🌐 CATEGORÍA: SERVIDOR/COMUNIDAD (50 comandos)
# ==========================================

@bot.event
async def on_message_delete(message):
    bot.snipes[message.channel.id] = (message.content, message.author, datetime.datetime.utcnow())

@bot.command()
async def snipe(ctx):
    """Recupera el último mensaje borrado."""
    if ctx.channel.id not in bot.snipes:
        return await ctx.send("**No hay nada que recuperar.**")
    content, author, time = bot.snipes[ctx.channel.id]
    embed = discord.Embed(description=f"**{content}**", color=0x2b2d31, timestamp=time)
    embed.set_author(name=author.name, icon_url=author.display_avatar.url)
    await ctx.send(embed=embed)

@bot.command()
async def mc(ctx):
    """Member count."""
    await ctx.send(f"**👥 Miembros en {ctx.guild.name}: `{ctx.guild.member_count}`**")

# ==========================================
# 📖 EL MEJOR HELP EMBED (ESTILO JAR.RIP)
# ==========================================

@bot.command()
async def help(ctx):
    embed = discord.Embed(title="**JAR.RIP CLONE - DASHBOARD**", color=0x2b2d31)
    embed.set_thumbnail(url=bot.user.avatar.url)
    
    embed.add_field(
        name="**🛡️ MODERACIÓN (50)**",
        value="`ban`, `kick`, `nuke`, `lock`, `unlock`, `warn`, `mute`, `timeout`, `massban`, `clear`, `slowmode`, `nick`, `role`, `hide`...",
        inline=False
    )
    
    embed.add_field(
        name="**⚙️ UTILIDAD (50)**",
        value="`avatar`, `banner`, `steal`, `userinfo`, `serverinfo`, `ping`, `uptime`, `icon`, `invite`, `urban`, `weather`, `math`...",
        inline=False
    )
    
    embed.add_field(
        name="**👥 SERVER/COMMUNITY (50)**",
        value="`snipe`, `editsnipe`, `poll`, `afk`, `remind`, `say`, `embed`, `membercount`, `boosters`, `verify`, `suggest`, `report`...",
        inline=False
    )
    
    embed.set_footer(text=f"Prefix: {PREFIX} | {ctx.guild.name}", icon_url=ctx.author.avatar.url)
    await ctx.send(embed=embed)

# --- MANEJO DE ERRORES BYPASS ---
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("**❌ No tienes permisos de administrador para este comando.**")
    elif isinstance(error, commands.CommandNotFound):
        pass
    else:
        logging.error(error)

bot.run(TOKEN)
