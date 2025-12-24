import discord
from discord.ext import commands
from discord import ui, Embed
import aiohttp
import os
import time
from datetime import datetime, timedelta

TOKEN = os.getenv("DISCORD_BOT_TOKEN")
PREFIX = "!"

intents = discord.Intents.all()
bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)

start_time = time.time()

# ================= EVENTOS =================
@bot.event
async def on_ready():
    print(f"Bot conectado como {bot.user}")
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="!help | Bot Bilingüe Profesional"))

# ================= HELP =================
@bot.command()
async def help(ctx):
    embed = Embed(title="Ayuda del Bot Profesional Bilingüe", color=0x2f3136)
    embed.add_field(name="Moderación", value="ban, unban, kick, softban, mute, unmute, timeout, untimeout, warn, warnings, clearwarns, lock, unlock, slowmode, rolelock, roleunlock, nick, resetnick, purge, clear, nuke, massban", inline=False)
    embed.add_field(name="Utilidad", value="ping, uptime, botinfo, serverinfo, userinfo, avatar, roles, channels, emojis, boosts, invite, afk, remind, calc, timestamp, poll, say, embed, weather, covid, translate, define, google, urban, randomfact, math, convert, timezones", inline=False)
    embed.add_field(name="Comunidad", value="reglas, ip, redes, staff, evento, eventos, sugerir, report, perfil, nivel, ranking, bienvenida, despedida, faq, horarios, donate, links, changelog, estado, topusers, serverstats, rolesstats, memes, quote", inline=False)
    embed.add_field(name="Panel", value="!panel | !comunidad", inline=False)
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

# ================= FUNCIONES AUXILIARES =================
async def check_permissions(ctx, member: discord.Member):
    if member.top_role >= ctx.me.top_role:
        await ctx.send("No puedo ejecutar esta acción sobre este usuario (rol superior o igual).")
        return False
    return True

# ================= MODERACIÓN =================
# Ejemplo detallado de comando moderación
@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason="No especificado"):
    if not await check_permissions(ctx, member): return
    try:
        await member.ban(reason=reason)
        embed = Embed(title=f"Usuario Baneado: {member}", color=0xED4245)
        embed.add_field(name="ID", value=member.id)
        embed.add_field(name="Motivo", value=reason)
        embed.add_field(name="Autor de la acción", value=ctx.author)
        embed.add_field(name="Fecha", value=datetime.utcnow().strftime("%d/%m/%Y %H:%M UTC"))
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"No se pudo banear al usuario: {e}")

# ================= UTILIDAD COMPLETA =================
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

# Weather detallado
@bot.command()
async def weather(ctx, *, location):
    async with aiohttp.ClientSession() as session:
        try:
            # Ejemplo con coordenadas fijas, se puede mejorar usando geocoding API
            url = f"https://api.open-meteo.com/v1/forecast?latitude=0&longitude=0&current_weather=true&timezone=auto"
            async with session.get(url) as r:
                data = await r.json()
            weather_data = data['current_weather']
            embed = Embed(title=f"Clima en {location}", color=0x57F287)
            embed.add_field(name="Temperatura", value=f"{weather_data['temperature']}°C")
            embed.add_field(name="Viento", value=f"{weather_data['windspeed']} km/h")
            embed.add_field(name="Dirección del viento", value=f"{weather_data['winddirection']}°")
            embed.add_field(name="Hora de la medición", value=weather_data['time'])
            await ctx.send(embed=embed, ephemeral=True)
        except:
            await ctx.send("Error consultando el clima.", ephemeral=True)

# Translate detallado
@bot.command()
async def translate(ctx, *, text):
    async with aiohttp.ClientSession() as session:
        try:
            payload = {"q": text, "source": "auto", "target": "es"}
            async with session.post("https://libretranslate.de/translate", data=payload) as r:
                data = await r.json()
            embed = Embed(title="Traducción", description=f"{data['translatedText']}", color=0x5865F2)
            embed.add_field(name="Texto original", value=text)
            await ctx.send(embed=embed, ephemeral=True)
        except:
            await ctx.send("Error traduciendo el texto.", ephemeral=True)

# Memes detallado
@bot.command()
async def memes(ctx):
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get("https://meme-api.com/gimme") as r:
                data = await r.json()
            embed = Embed(title=data['title'], url=data['postLink'], color=0xEB459E)
            embed.set_image(url=data['url'])
            embed.add_field(name="Subreddit", value=data['subreddit'])
            embed.add_field(name="Autor", value=data['author'])
            embed.add_field(name="Upvotes", value=data['ups'])
            embed.add_field(name="NSFW", value=str(data['nsfw']))
            await ctx.send(embed=embed, ephemeral=True)
        except:
            await ctx.send("Error obteniendo un meme.", ephemeral=True)

# ================= RUN =================
bot.run(TOKEN)
