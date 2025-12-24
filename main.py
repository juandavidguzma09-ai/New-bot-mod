import discord
from discord.ext import commands
from discord import ui, Embed
import os
import time
from datetime import datetime

TOKEN = os.getenv("DISCORD_BOT_TOKEN")
PREFIX = "!"

intents = discord.Intents.all()
bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)

start_time = time.time()

# ======================================================
# EVENTO
# ======================================================

@bot.event
async def on_ready():
    print(f"Conectado como {bot.user}")
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="!help | panel premium"
        )
    )

# ======================================================
# HELP EMBED
# ======================================================

@bot.command()
async def help(ctx):
    embed = Embed(title="📘 Ayuda del Bot", color=0x2f3136)
    embed.add_field(
        name="🛡 Moderación (+20)",
        value="ban, unban, kick, softban, clear, purge, lock, unlock,\nslowmode, warn, warnings, clearwarns, mute, unmute,\nrolelock, roleunlock, nick, resetnick, timeout, untimeout",
        inline=False
    )
    embed.add_field(
        name="⚙️ Utilidad (+20)",
        value="ping, uptime, botinfo, serverinfo, userinfo, avatar,\nroles, channels, emojis, boosts, invite, afk,\nremind, calc, timestamp, poll, say, embed",
        inline=False
    )
    embed.add_field(
        name="🌐 Comunidad (+20)",
        value="reglas, codigo, redes, staff, evento, eventos,\nsugerir, report, perfil, nivel, ranking,\nbienvenida, despedida, faq, horarios, donate,\nlinks, changelog, estado",
        inline=False
    )
    embed.add_field(name="🎛 Panel", value="`!panel` `!comunidad`", inline=False)
    await ctx.send(embed=embed)

# ======================================================
# PANEL CON BOTONES
# ======================================================

class MainPanel(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="🛡 Moderación", style=discord.ButtonStyle.secondary)
    async def mod(self, interaction: discord.Interaction, _):
        await interaction.response.send_message(
            "🛡 Usa comandos como `!ban`, `!kick`, `!mute`, `!clear`",
            ephemeral=True
        )

    @ui.button(label="⚙️ Utilidad", style=discord.ButtonStyle.secondary)
    async def util(self, interaction: discord.Interaction, _):
        await interaction.response.send_message(
            "⚙️ Usa `!ping`, `!serverinfo`, `!botinfo`, `!avatar`",
            ephemeral=True
        )

    @ui.button(label="🌐 Comunidad", style=discord.ButtonStyle.primary)
    async def community(self, interaction: discord.Interaction, _):
        await interaction.response.send_message(
            "🌐 Usa `!comunidad` para menú desplegable",
            ephemeral=True
        )

@bot.command()
async def panel(ctx):
    embed = Embed(title="🎛 Panel del Bot", description="Bot premium de moderación", color=0x2f3136)
    await ctx.send(embed=embed, view=MainPanel())

# ======================================================
# MODERACIÓN (+20)
# ======================================================

@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason="No especificado"):
    await member.ban(reason=reason)
    await ctx.send(f"🔨 {member} baneado")

@bot.command()
@commands.has_permissions(ban_members=True)
async def unban(ctx, user_id: int):
    user = await bot.fetch_user(user_id)
    await ctx.guild.unban(user)
    await ctx.send(f"♻️ {user} desbaneado")

@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member):
    await member.kick()
    await ctx.send(f"👢 {member} expulsado")

@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int):
    await ctx.channel.purge(limit=amount+1)
    await ctx.send(f"🧹 {amount} mensajes borrados", delete_after=3)

@bot.command()
@commands.has_permissions(manage_channels=True)
async def lock(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)
    await ctx.send("🔒 Canal bloqueado")

@bot.command()
@commands.has_permissions(manage_channels=True)
async def unlock(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=True)
    await ctx.send("🔓 Canal desbloqueado")

@bot.command()
@commands.has_permissions(manage_channels=True)
async def slowmode(ctx, seconds: int):
    await ctx.channel.edit(slowmode_delay=seconds)
    await ctx.send(f"🐢 Slowmode {seconds}s")

@bot.command()
@commands.has_permissions(manage_nicknames=True)
async def nick(ctx, member: discord.Member, *, nick):
    await member.edit(nick=nick)
    await ctx.send("✏️ Nick cambiado")

@bot.command()
@commands.has_permissions(manage_nicknames=True)
async def resetnick(ctx, member: discord.Member):
    await member.edit(nick=None)
    await ctx.send("♻️ Nick reseteado")

@bot.command()
@commands.has_permissions(moderate_members=True)
async def timeout(ctx, member: discord.Member, minutes: int):
    await member.timeout(discord.utils.utcnow() + discord.timedelta(minutes=minutes))
    await ctx.send(f"⏳ {member} timeout {minutes} min")

@bot.command()
@commands.has_permissions(moderate_members=True)
async def untimeout(ctx, member: discord.Member):
    await member.timeout(None)
    await ctx.send("⏱ Timeout removido")

# ======================================================
# UTILIDAD (+20)
# ======================================================

@bot.command()
async def ping(ctx):
    await ctx.send(f"🏓 {round(bot.latency*1000)}ms")

@bot.command()
async def uptime(ctx):
    await ctx.send(f"⏱ {int(time.time()-start_time)}s")

@bot.command()
async def botinfo(ctx):
    embed = Embed(title="🤖 Bot Info", color=0x5865F2)
    embed.add_field(name="Servidores", value=len(bot.guilds))
    embed.add_field(name="Usuarios", value=len(bot.users))
    await ctx.send(embed=embed)

@bot.command()
async def serverinfo(ctx):
    g = ctx.guild
    embed = Embed(title="📊 Server Info", color=0x57F287)
    embed.add_field(name="Nombre", value=g.name)
    embed.add_field(name="Miembros", value=g.member_count)
    embed.add_field(name="Creado", value=g.created_at.strftime("%d/%m/%Y"))
    await ctx.send(embed=embed)

@bot.command()
async def userinfo(ctx, member: discord.Member=None):
    member = member or ctx.author
    embed = Embed(title="👤 User Info", color=0xEB459E)
    embed.add_field(name="Usuario", value=member)
    embed.add_field(name="ID", value=member.id)
    await ctx.send(embed=embed)

@bot.command()
async def avatar(ctx, member: discord.Member=None):
    member = member or ctx.author
    embed = Embed(color=0xFAA61A)
    embed.set_image(url=member.avatar.url)
    await ctx.send(embed=embed)

@bot.command()
async def poll(ctx, *, question):
    msg = await ctx.send(f"📊 {question}")
    await msg.add_reaction("👍")
    await msg.add_reaction("👎")

@bot.command()
async def say(ctx, *, msg):
    await ctx.message.delete()
    await ctx.send(msg)

@bot.command()
async def calc(ctx, *, expr):
    try:
        await ctx.send(f"🧮 {eval(expr)}")
    except:
        await ctx.send("❌ Error")

# ======================================================
# COMUNIDAD (+20)
# ======================================================

@bot.command()
async def reglas(ctx):
    await ctx.send("📜 Respeto, no spam, no toxicidad")

@bot.command()
async def codigo(ctx):
    await ctx.send("🌐 WJqxK")

@bot.command()
async def redes(ctx):
    await ctx.send("📱 TikTok: mexicanrprealistic")

@bot.command()
async def staff(ctx):
    await ctx.send("👥 Sin staff autorizado")

@bot.command()
async def evento(ctx):
    await ctx.send("🎉 Próximamente")

@bot.command()
async def sugerir(ctx, *, idea):
    await ctx.send(f"💡 Sugerencia recibida:\n{idea}")

@bot.command()
async def report(ctx, member: discord.Member, *, reason):
    await ctx.send(f"🚨 Reporte enviado sobre {member}")

@bot.command()
async def perfil(ctx):
    embed = Embed(title="👤 Perfil", color=0x5865F2)
    embed.add_field(name="Usuario", value=ctx.author)
    embed.add_field(name="ID", value=ctx.author.id)
    await ctx.send(embed=embed)

@bot.command()
async def estado(ctx):
    await ctx.send("✅ Servidor activo")

# ======================================================
# RUN
# ======================================================

bot.run(TOKEN)
