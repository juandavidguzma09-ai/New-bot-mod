import discord
from discord.ext import commands
from discord import ui, Embed
import os
import time
from datetime import datetime

TOKEN = os.getenv("DISCORD_BOT_TOKEN")
PREFIX = "."

intents = discord.Intents.all()
bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)

start_time = time.time()

# ================= EVENTO =================

@bot.event
async def on_ready():
    print(f"Conectado como {bot.user}")
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="!help | Panel Premium"
        )
    )

# ================= HELP =================

@bot.command()
async def help(ctx):
    embed = Embed(title="📘 Ayuda del Bot", color=0x2f3136)
    embed.add_field(
        name="🛡 Moderación",
        value="ban, unban, kick, softban, clear, purge, lock, unlock, slowmode, warn, warnings, clearwarns, mute, unmute, rolelock, roleunlock, nick, resetnick, timeout, untimeout",
        inline=False
    )
    embed.add_field(
        name="⚙️ Utilidad",
        value="ping, uptime, botinfo, serverinfo, userinfo, avatar, roles, channels, emojis, boosts, invite, afk, remind, calc, timestamp, poll, say, embed",
        inline=False
    )
    embed.add_field(
        name="🌐 Comunidad",
        value="reglas, ip, redes, staff, evento, eventos, sugerir, report, perfil, nivel, ranking, bienvenida, despedida, faq, horarios, donate, links, changelog, estado",
        inline=False
    )
    embed.add_field(name="🎛 Panel", value="`!panel` `!comunidad`", inline=False)
    await ctx.send(embed=embed)

# ================= PANEL BOTONES =================

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
    embed = Embed(title="🎛 Panel del Bot", description="Bot premium de moderación y utilidad", color=0x2f3136)
    await ctx.send(embed=embed, view=MainPanel())

# ================= MENÚ COMUNIDAD =================

class CommunitySelect(ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="📜 Reglas", value="rules"),
            discord.SelectOption(label="📢 Anuncios", value="announcements"),
            discord.SelectOption(label="🎉 Eventos", value="events"),
            discord.SelectOption(label="🆘 Soporte", value="support"),
            discord.SelectOption(label="👥 Staff", value="staff"),
        ]
        super().__init__(placeholder="Selecciona una opción…", options=options)

    async def callback(self, interaction: discord.Interaction):
        data = {
            "rules": ("📜 Reglas", "Respeta, no hagas spam, no seas tóxico."),
            "announcements": ("📢 Anuncios", "Mantente atento a las novedades del servidor."),
            "events": ("🎉 Eventos", "No hay eventos activos actualmente."),
            "support": ("🆘 Soporte", "Contacta a un miembro del staff si necesitas ayuda."),
            "staff": ("👥 Staff", "Owner, Admins, Moderadores")
        }
        title, desc = data[self.values[0]]
        embed = Embed(title=title, description=desc, color=0x5865F2)
        await interaction.response.send_message(embed=embed, ephemeral=True)

class CommunityMenu(ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(CommunitySelect())

@bot.command()
async def comunidad(ctx):
    embed = Embed(title="🌐 Comunidad", description="Selecciona una opción en el menú desplegable", color=0x2f3136)
    await ctx.send(embed=embed, view=CommunityMenu())

# ================= MODERACIÓN =================

async def check_permissions(ctx, member: discord.Member):
    if member.top_role >= ctx.me.top_role:
        await ctx.send("❌ No puedo ejecutar la acción sobre este usuario (rol superior).")
        return False
    return True

@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason="No especificado"):
    if not await check_permissions(ctx, member):
        return
    try:
        await member.ban(reason=reason)
        await ctx.send(f"🔨 {member} baneado | Razón: {reason}")
    except Exception as e:
        await ctx.send(f"❌ Error: {e}")

@bot.command()
@commands.has_permissions(ban_members=True)
async def unban(ctx, user_id: int):
    try:
        user = await bot.fetch_user(user_id)
        await ctx.guild.unban(user)
        await ctx.send(f"♻️ {user} desbaneado")
    except Exception as e:
        await ctx.send(f"❌ Error: {e}")

@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member):
    if not await check_permissions(ctx, member):
        return
    try:
        await member.kick()
        await ctx.send(f"👢 {member} expulsado")
    except Exception as e:
        await ctx.send(f"❌ Error: {e}")

@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int):
    try:
        await ctx.channel.purge(limit=amount+1)
        await ctx.send(f"🧹 {amount} mensajes borrados", delete_after=3)
    except Exception as e:
        await ctx.send(f"❌ Error: {e}")

@bot.command()
@commands.has_permissions(manage_channels=True)
async def lock(ctx):
    try:
        await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)
        await ctx.send("🔒 Canal bloqueado")
    except Exception as e:
        await ctx.send(f"❌ Error: {e}")

@bot.command()
@commands.has_permissions(manage_channels=True)
async def unlock(ctx):
    try:
        await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=True)
        await ctx.send("🔓 Canal desbloqueado")
    except Exception as e:
        await ctx.send(f"❌ Error: {e}")

@bot.command()
@commands.has_permissions(moderate_members=True)
async def mute(ctx, member: discord.Member, minutes: int=10):
    if not await check_permissions(ctx, member):
        return
    try:
        await member.timeout(duration=minutes*60)
        await ctx.send(f"🔇 {member} silenciado por {minutes} minutos")
    except Exception as e:
        await ctx.send(f"❌ Error: {e}")

@bot.command()
@commands.has_permissions(moderate_members=True)
async def unmute(ctx, member: discord.Member):
    if not await check_permissions(ctx, member):
        return
    try:
        await member.timeout(None)
        await ctx.send(f"🔊 {member} desmuted")
    except Exception as e:
        await ctx.send(f"❌ Error: {e}")

# ================= UTILIDAD =================

@bot.command()
async def ping(ctx):
    await ctx.send(f"🏓 Pong: {round(bot.latency*1000)}ms")

@bot.command()
async def uptime(ctx):
    seconds = int(time.time() - start_time)
    await ctx.send(f"⏱ Uptime: {seconds}s")

@bot.command()
async def botinfo(ctx):
    embed = Embed(title="🤖 Bot Info", color=0x5865F2)
    embed.add_field(name="Servidores", value=len(bot.guilds))
    embed.add_field(name="Usuarios", value=len(bot.users))
    await ctx.send(embed=embed)

@bot.command()
async def serverinfo(ctx):
    g = ctx.guild
    embed = Embed(title=f"📊 Información de {g.name}", color=0x57F287)
    embed.set_thumbnail(url=g.icon.url if g.icon else None)
    embed.add_field(name="ID", value=g.id)
    embed.add_field(name="Owner", value=g.owner)
    embed.add_field(name="Miembros", value=g.member_count)
    embed.add_field(name="Boosts", value=f"{g.premium_subscription_count} | Nivel {g.premium_tier}")
    embed.add_field(name="Roles", value=len(g.roles))
    embed.add_field(name="Canales", value=len(g.channels))
    embed.add_field(name="Creado", value=g.created_at.strftime("%d/%m/%Y"))
    embed.set_footer(text=f"Emojis: {len(g.emojis)}")
    await ctx.send(embed=embed)

@bot.command()
async def userinfo(ctx, member: discord.Member=None):
    member = member or ctx.author
    embed = Embed(title=f"👤 Información de {member}", color=0xEB459E)
    embed.set_thumbnail(url=member.avatar.url if member.avatar else None)
    embed.add_field(name="ID", value=member.id)
    embed.add_field(name="Cuenta creada", value=member.created_at.strftime("%d/%m/%Y"))
    embed.add_field(name="Roles", value=", ".join([r.name for r in member.roles[1:]]))
    embed.add_field(name="Estado", value=str(member.status))
    await ctx.send(embed=embed)

@bot.command()
async def avatar(ctx, member: discord.Member=None):
    member = member or ctx.author
    embed = Embed(title=f"🖼 Avatar de {member}", color=0xFAA61A)
    embed.set_image(url=member.avatar.url)
    await ctx.send(embed=embed)

# ================= COMUNIDAD =================

@bot.command()
async def reglas(ctx):
    await ctx.send("📜 Respeta, no hagas spam, no seas tóxico")

@bot.command()
async def ip(ctx):
    await ctx.send("🌐 Aqui tienes nuestro codigo: WJqxK")

@bot.command()
async def redes(ctx):
    await ctx.send("📱 TikTok: mexicanrprealistic ")

@bot.command()
async def staff(ctx):
    await ctx.send("👥 No autorizados")

@bot.command()
async def evento(ctx):
    await ctx.send("🎉 no hay eventos")

@bot.command()
async def sugerir(ctx, *, idea):
    await ctx.send(f"💡 Sugerencia recibida:\n{idea}")

@bot.command()
async def report(ctx, member: discord.Member, *, reason):
    await ctx.send(f"🚨 Reporte enviado sobre {member} | Razón: {reason}")

@bot.command()
async def perfil(ctx):
    embed = Embed(title=f"👤 Perfil de {ctx.author}", color=0x5865F2)
    embed.add_field(name="ID", value=ctx.author.id)
    embed.add_field(name="Cuenta creada", value=ctx.author.created_at.strftime("%d/%m/%Y"))
    await ctx.send(embed=embed)

@bot.command()
async def estado(ctx):
    await ctx.send("✅ Servidor activo")

# ================= RUN =================

bot.run(TOKEN)
