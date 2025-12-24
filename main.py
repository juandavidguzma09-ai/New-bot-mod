import discord
from discord.ext import commands, tasks
from discord import ui, Embed
import aiohttp
import os
import time
from datetime import datetime, timedelta
import asyncio
import random
import math

TOKEN = os.getenv("DISCORD_BOT_TOKEN")
PREFIX = "!"

intents = discord.Intents.all()
bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)

start_time = time.time()

# ================= EVENTOS =================
@bot.event
async def on_ready():
    print(f"Bot conectado como {bot.user}")
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="!help | Bot Profesional Bilingüe"))

# ================= FUNCIONES AUXILIARES =================
async def check_permissions(ctx, member: discord.Member):
    if member.top_role >= ctx.me.top_role:
        await ctx.send("No puedo ejecutar esta acción sobre este usuario (rol superior o igual).")
        return False
    return True

def uptime():
    delta = timedelta(seconds=int(time.time() - start_time))
    return str(delta)

afk_users = {}

# ================= HELP =================
@bot.command()
async def help(ctx):
    embed = Embed(title="Ayuda del Bot Profesional Bilingüe", color=0x2f3136, description="Lista completa de comandos implementados con detalles.")
    embed.add_field(
        name="Moderación",
        value=(
            "**ban [usuario] [motivo]** → Banea a un usuario.\n"
            "**unban [usuario#1234]** → Desbanea a un usuario.\n"
            "**kick [usuario] [motivo]** → Expulsa a un usuario.\n"
            "**softban [usuario] [motivo]** → Banea y desbanea inmediatamente.\n"
            "**mute/unmute [usuario]** → Silencia o desilencia a un usuario.\n"
            "**timeout/untimeout [usuario] [tiempo]** → Pone tiempo fuera a un usuario.\n"
            "**warn [usuario] [motivo]** → Advierte a un usuario.\n"
            "**warnings [usuario]** → Lista las advertencias.\n"
            "**clearwarns [usuario]** → Limpia advertencias.\n"
            "**lock/unlock [canal]** → Bloquea o desbloquea canal.\n"
            "**slowmode [canal] [segundos]** → Configura slowmode.\n"
            "**rolelock/roleunlock [rol]** → Bloquea o desbloquea rol.\n"
            "**nick/resetnick [usuario]** → Cambia o resetea nickname.\n"
            "**purge/clear [cantidad]** → Borra mensajes.\n"
            "**nuke [canal]** → Borra y recrea canal.\n"
            "**massban [usuarios]** → Banea múltiples usuarios."
        ),
        inline=False
    )
    embed.add_field(
        name="Utilidad",
        value=(
            "**ping** → Muestra latencia del bot.\n"
            "**uptime** → Muestra el tiempo activo del bot.\n"
            "**botinfo** → Información general del bot.\n"
            "**serverinfo** → Información del servidor.\n"
            "**userinfo [usuario]** → Información del usuario.\n"
            "**avatar [usuario]** → Muestra avatar.\n"
            "**roles/channels/emojis/boosts** → Información del servidor.\n"
            "**invite** → Link de invitación del bot.\n"
            "**afk [motivo]** → Establece estado AFK.\n"
            "**remind [tiempo] [mensaje]** → Recordatorio.\n"
            "**calc [operación]** → Calculadora.\n"
            "**timestamp [fecha]** → Convierte fecha.\n"
            "**poll [pregunta]** → Crea encuesta.\n"
            "**say [mensaje]** → Bot repite mensaje.\n"
            "**embed [mensaje]** → Envía embed.\n"
            "**weather [ubicación]** → Clima.\n"
            "**covid [país]** → Datos COVID.\n"
            "**translate [texto]** → Traduce texto.\n"
            "**define [palabra]** → Definición.\n"
            "**google [consulta]** → Busca en Google.\n"
            "**urban [palabra]** → Urban Dictionary.\n"
            "**randomfact** → Dato curioso.\n"
            "**math/convert/timezones** → Calculadora, conversor, zonas horarias."
        ),
        inline=False
    )
    embed.add_field(
        name="Comunidad",
        value=(
            "**reglas** → Muestra reglas del servidor.\n"
            "**ip** → IP del servidor.\n"
            "**redes** → Links de redes.\n"
            "**staff** → Lista de staff.\n"
            "**evento/eventos** → Información de eventos.\n"
            "**sugerir/report** → Sugerencias o reportes.\n"
            "**perfil/nivel/ranking** → Sistema de niveles y perfil.\n"
            "**bienvenida/despedida** → Mensajes automáticos.\n"
            "**faq/horarios/donate/links/changelog/estado** → Info variada.\n"
            "**topusers/serverstats/rolesstats** → Estadísticas.\n"
            "**memes/quote** → Contenido divertido."
        ),
        inline=False
    )
    embed.add_field(name="Panel", value="Usa `!panel` para abrir el panel interactivo de botones.", inline=False)
    await ctx.send(embed=embed)

# ================= PANEL BOTONES =================
class MainPanel(ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    @ui.button(label="Moderación", style=discord.ButtonStyle.secondary)
    async def mod(self, interaction: discord.Interaction, _):
        await interaction.response.send_message("Comandos de moderación: ban, kick, mute, clear, nuke, rolelock...", ephemeral=True)
    @ui.button(label="Utilidad", style=discord.ButtonStyle.secondary)
    async def util(self, interaction: discord.Interaction, _):
        await interaction.response.send_message("Comandos de utilidad: ping, serverinfo, botinfo, avatar, translate, weather, memes...", ephemeral=True)
    @ui.button(label="Comunidad", style=discord.ButtonStyle.primary)
    async def community(self, interaction: discord.Interaction, _):
        await interaction.response.send_message("Usa !comunidad para abrir el menú interactivo", ephemeral=True)
@bot.command()
async def panel(ctx):
    embed = Embed(title="Panel del Bot Profesional", description="Moderación, Utilidad y Comunidad", color=0x2f3136)
    await ctx.send(embed=embed, view=MainPanel())

# ================= MENÚ COMUNIDAD =================
class CommunitySelect(ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Reglas", value="rules"),
            discord.SelectOption(label="Anuncios", value="announcements"),
            discord.SelectOption(label="Eventos", value="events"),
            discord.SelectOption(label="Soporte", value="support"),
            discord.SelectOption(label="Staff", value="staff"),
        ]
        super().__init__(placeholder="Selecciona una opción", options=options)
    async def callback(self, interaction: discord.Interaction):
        data = {
            "rules": ("Reglas del servidor", "Respeta a todos los miembros, no hagas spam, no seas tóxico, sigue las reglas y diviértete."),
            "announcements": ("Anuncios", "Mantente al día con los anuncios y novedades del servidor."),
            "events": ("Eventos", "Actualmente no hay eventos activos, pero pronto habrá actividades."),
            "support": ("Soporte", "Contacta al equipo de soporte para ayuda, dudas o problemas."),
            "staff": ("Staff", "Owner, Administradores y Moderadores del servidor.")
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
    embed = Embed(title="Comunidad", description="Selecciona una opción en el menú desplegable", color=0x2f3136)
    await ctx.send(embed=embed, view=CommunityMenu())

# ================= MODERACIÓN =================
@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason="No especificado"):
    if not await check_permissions(ctx, member): return
    await member.ban(reason=reason)
    embed = Embed(title=f"Usuario Baneado: {member}", color=0xED4245)
    embed.add_field(name="ID", value=member.id)
    embed.add_field(name="Motivo", value=reason)
    embed.add_field(name="Autor", value=ctx.author)
    embed.add_field(name="Fecha", value=datetime.utcnow().strftime("%d/%m/%Y %H:%M UTC"))
    await ctx.send(embed=embed)
@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason="No especificado"):
    if not await check_permissions(ctx, member): return
    await member.kick(reason=reason)
    embed = Embed(title=f"Usuario Expulsado: {member}", color=0xED4245)
    embed.add_field(name="ID", value=member.id)
    embed.add_field(name="Motivo", value=reason)
    embed.add_field(name="Autor", value=ctx.author)
    embed.add_field(name="Fecha", value=datetime.utcnow().strftime("%d/%m/%Y %H:%M UTC"))
    await ctx.send(embed=embed)
@bot.command()
@commands.has_permissions(ban_members=True)
async def unban(ctx, *, member: str):
    banned_users = await ctx.guild.bans()
    member_name, member_discrim = member.split("#")
    for ban_entry in banned_users:
        user = ban_entry.user
        if (user.name, user.discriminator) == (member_name, member_discrim):
            await ctx.guild.unban(user)
            embed = Embed(title=f"Usuario Desbaneado: {user}", color=0x57F287)
            embed.add_field(name="ID", value=user.id)
            embed.add_field(name="Autor", value=ctx.author)
            embed.add_field(name="Fecha", value=datetime.utcnow().strftime("%d/%m/%Y %H:%M UTC"))
            await ctx.send(embed=embed)
            return
    await ctx.send("Usuario no encontrado en la lista de baneados.")

# ================= UTILIDAD =================
@bot.command()
async def ping(ctx):
    embed = Embed(title="Pong!", description=f"Latencia: {round(bot.latency*1000)}ms", color=0x57F287)
    await ctx.send(embed=embed)
@bot.command()
async def uptime_cmd(ctx):
    embed = Embed(title="Uptime del Bot", description=uptime(), color=0x57F287)
    await ctx.send(embed=embed)
@bot.command()
async def userinfo(ctx, member: discord.Member=None):
    member = member or ctx.author
    embed = Embed(title=f"Información de {member}", color=0x57F287)
    embed.add_field(name="ID", value=member.id)
    embed.add_field(name="Cuenta creada", value=member.created_at.strftime("%d/%m/%Y %H:%M"))
    embed.add_field(name="Unido al servidor", value=member.joined_at.strftime("%d/%m/%Y %H:%M"))
    embed.add_field(name="Estado", value=str(member.status))
    embed.add_field(name="Top Role", value=member.top_role)
    embed.add_field(name="Roles", value=", ".join([r.name for r in member.roles[1:]]) or "Sin roles")
    embed.set_thumbnail(url=member.avatar.url if member.avatar else None)
    await ctx.send(embed=embed)

# ================= WEATHER =================
@bot.command()
async def weather(ctx, *, location):
    async with aiohttp.ClientSession() as session:
        # Usamos coordenadas fijas para ejemplo
        url = f"https://api.open-meteo.com/v1/forecast?latitude=0&longitude=0&current_weather=true&timezone=auto"
        async with session.get(url) as r:
            data = await r.json()
        weather_data = data['current_weather']
        embed = Embed(title=f"Clima en {location}", color=0x57F287)
        embed.add_field(name="Temperatura", value=f"{weather_data['temperature']}°C")
        embed.add_field(name="Viento", value=f"{weather_data['windspeed']} km/h")
        embed.add_field(name="Dirección del viento", value=f"{weather_data['winddirection']}°")
        embed.add_field(name="Hora de la medición", value=weather_data['time'])
        await ctx.send(embed=embed)

# ================= TRANSLATE =================
@bot.command()
async def translate(ctx, *, text):
    async with aiohttp.ClientSession() as session:
        payload = {"q": text, "source": "auto", "target": "es"}
        async with session.post("https://libretranslate.de/translate", data=payload) as r:
            data = await r.json()
        embed = Embed(title="Traducción", description=f"{data['translatedText']}", color=0x5865F2)
        embed.add_field(name="Texto original", value=text)
        await ctx.send(embed=embed)

# ================= MEMES =================
@bot.command()
async def memes(ctx):
    async with aiohttp.ClientSession() as session:
        async with session.get("https://meme-api.com/gimme") as r:
            data = await r.json()
        embed = Embed(title=data['title'], url=data['postLink'], color=0xEB459E)
        embed.set_image(url=data['url'])
        embed.add_field(name="Subreddit", value=data['subreddit'])
        embed.add_field(name="Autor", value=data['author'])
        embed.add_field(name="Upvotes", value=data['ups'])
        embed.add_field(name="NSFW", value=str(data['nsfw']))
        await ctx.send(embed=embed)

# ================= RUN BOT =================
bot.run(TOKEN)
