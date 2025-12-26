import discord
from discord.ext import commands
import datetime
import asyncio
import aiosqlite
import random
import io
import os

TOKEN = os.getenv("TOKEN")
DEFAULT_PREFIX = "$"

# Intents necesarios para moderación y miembros
intents = discord.Intents.all()

class UltimateBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=self.get_prefix,
            intents=intents,
            help_command=None,  # Haremos un help personalizado
            case_insensitive=True
        )
        self.sniped_messages = {}
        self.editsniped_messages = {}
        self.start_time = datetime.datetime.now()

    async def get_prefix(self, message):
        if not message.guild:
            return DEFAULT_PREFIX
        async with aiosqlite.connect("bot_database.db") as db:
            async with db.execute("SELECT prefix FROM guilds WHERE guild_id = ?", (message.guild.id,)) as cursor:
                result = await cursor.fetchone()
                return result[0] if result else DEFAULT_PREFIX

    async def setup_hook(self):
        # Inicializar Base de Datos
        async with aiosqlite.connect("bot_database.db") as db:
            # Tabla de configuración de servidor
            await db.execute("""
                CREATE TABLE IF NOT EXISTS guilds (
                    guild_id INTEGER PRIMARY KEY,
                    prefix TEXT DEFAULT '$',
                    log_channel INTEGER
                )
            """)
            # Tabla de Advertencias
            await db.execute("""
                CREATE TABLE IF NOT EXISTS warns (
                    warn_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    guild_id INTEGER,
                    moderator_id INTEGER,
                    reason TEXT,
                    timestamp TEXT
                )
            """)
            await db.commit()
        print(f"--- Base de datos inicializada ---")

bot = UltimateBot()

# ==============================================================================
# EVENTOS
# ==============================================================================

@bot.event
async def on_ready():
    print(f"Conectado como {bot.user} (ID: {bot.user.id})")
    print(f"Total de comandos: {len(bot.commands)}")
    print("--- El Bot está listo para moderar ---")
    await bot.change_presence(activity=discord.Game(name=f"Protegiendo {len(bot.guilds)} servidores | $help"))

@bot.event
async def on_message_delete(message):
    if message.author.bot: return
    bot.sniped_messages[message.channel.id] = {
        "content": message.content,
        "author": message.author,
        "time": datetime.datetime.now()
    }

@bot.event
async def on_message_edit(before, after):
    if before.author.bot: return
    bot.editsniped_messages[before.channel.id] = {
        "before": before.content,
        "after": after.content,
        "author": before.author
    }

# ==============================================================================
# UTILIDADES INTERNAS (HELPERS)
# ==============================================================================

def create_embed(title, description, color=discord.Color.blue()):
    embed = discord.Embed(title=title, description=description, color=color)
    embed.set_footer(text="Shadow Mod Bot")
    embed.timestamp = datetime.datetime.now()
    return embed

async def log_action(guild, title, description, color=discord.Color.red()):
    async with aiosqlite.connect("bot_database.db") as db:
        async with db.execute("SELECT log_channel FROM guilds WHERE guild_id = ?", (guild.id,)) as cursor:
            result = await cursor.fetchone()
            if result and result[0]:
                channel = guild.get_channel(result[0])
                if channel:
                    embed = create_embed(title, description, color)
                    await channel.send(embed=embed)

# ==============================================================================
# COMANDOS DE MODERACIÓN (HARD)
# ==============================================================================

@bot.command(name="kick")
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason="No especificada"):
    if member.top_role >= ctx.author.top_role:
        return await ctx.send("❌ No puedes expulsar a alguien con un rol igual o superior al tuyo.")
    
    await member.kick(reason=reason)
    embed = create_embed("Usuario Expulsado", f"👤 **Usuario:** {member}\n👮 **Mod:** {ctx.author}\n📝 **Razón:** {reason}", discord.Color.orange())
    await ctx.send(embed=embed)
    await log_action(ctx.guild, "Kick", f"{member} fue expulsado por {ctx.author}. Razón: {reason}")

@bot.command(name="ban")
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason="No especificada"):
    if member.top_role >= ctx.author.top_role:
        return await ctx.send("❌ No puedes banear a alguien con un rol igual o superior al tuyo.")

    await member.ban(reason=reason)
    embed = create_embed("Usuario Baneado", f"👤 **Usuario:** {member}\n👮 **Mod:** {ctx.author}\n📝 **Razón:** {reason}", discord.Color.red())
    await ctx.send(embed=embed)
    await log_action(ctx.guild, "Ban", f"{member} fue baneado por {ctx.author}. Razón: {reason}")

@bot.command(name="softban")
@commands.has_permissions(ban_members=True)
async def softban(ctx, member: discord.Member, *, reason="Softban (Borrado de mensajes)"):
    # Banea y desbanea para borrar mensajes
    await member.ban(reason=reason, delete_message_days=7)
    await ctx.guild.unban(member)
    await ctx.send(embed=create_embed("Softban Exitoso", f"{member} fue soft-baneado (kick + limpieza de mensajes)."))

@bot.command(name="unban")
@commands.has_permissions(ban_members=True)
async def unban(ctx, *, user_input):
    # Intenta buscar por ID o Nombre
    banned_users = [entry async for entry in ctx.guild.bans()]
    
    for ban_entry in banned_users:
        user = ban_entry.user
        if str(user.id) == user_input or user.name == user_input:
            await ctx.guild.unban(user)
            await ctx.send(embed=create_embed("Usuario Desbaneado", f"{user.mention} ha sido perdonado."))
            return
    
    await ctx.send("❌ Usuario no encontrado en la lista de bans.")

@bot.command(name="timeout", aliases=["mute"])
@commands.has_permissions(moderate_members=True)
async def timeout(ctx, member: discord.Member, time_str: str, *, reason="No especificada"):
    # Formato simple: 10m, 1h, 24h
    time_units = {"m": 60, "h": 3600, "d": 86400}
    unit = time_str[-1]
    value = int(time_str[:-1])
    
    if unit not in time_units:
        return await ctx.send("Uso: !timeout @usuario 10m Razón")

    seconds = value * time_units[unit]
    duration = datetime.timedelta(seconds=seconds)
    
    await member.timeout(duration, reason=reason)
    await ctx.send(embed=create_embed("Usuario Aislado (Timeout)", f"{member.mention} silenciado por {time_str}.\nRazón: {reason}", discord.Color.dark_grey()))

@bot.command(name="unmute", aliases=["untimeout"])
@commands.has_permissions(moderate_members=True)
async def unmute(ctx, member: discord.Member):
    await member.timeout(None, reason="Unmute manual")
    await ctx.send(f"🔊 {member.mention} ya puede hablar.")

@bot.command(name="purge", aliases=["clear"])
@commands.has_permissions(manage_messages=True)
async def purge(ctx, amount: int):
    if amount > 100: amount = 100
    deleted = await ctx.channel.purge(limit=amount + 1)
    msg = await ctx.send(f"🗑️ Se han borrado {len(deleted)-1} mensajes.")
    await asyncio.sleep(3)
    await msg.delete()

@bot.command(name="nuke")
@commands.has_permissions(administrator=True)
async def nuke(ctx):
    # Clona el canal y borra el viejo
    channel_pos = ctx.channel.position
    new_channel = await ctx.channel.clone(reason="Nuke command")
    await new_channel.edit(position=channel_pos)
    await ctx.channel.delete()
    await new_channel.send("☢️ **ESTE CANAL HA SIDO NUKEADO** ☢️\nhttps://media.giphy.com/media/HhTXt43pk1I1W/giphy.gif")

# ==============================================================================
# GESTIÓN DE CANALES Y ROLES
# ==============================================================================

@bot.command(name="lock")
@commands.has_permissions(manage_channels=True)
async def lock(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)
    await ctx.send("🔒 Canal bloqueado.")

@bot.command(name="unlock")
@commands.has_permissions(manage_channels=True)
async def unlock(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=True)
    await ctx.send("🔓 Canal desbloqueado.")

@bot.command(name="slowmode")
@commands.has_permissions(manage_channels=True)
async def slowmode(ctx, seconds: int):
    await ctx.channel.edit(slowmode_delay=seconds)
    await ctx.send(f"🐢 Slowmode establecido a {seconds} segundos.")

@bot.command(name="addrole")
@commands.has_permissions(manage_roles=True)
async def addrole(ctx, member: discord.Member, role: discord.Role):
    if ctx.author.top_role <= role:
        return await ctx.send("❌ No puedes dar un rol superior al tuyo.")
    await member.add_roles(role)
    await ctx.send(f"✅ Rol {role.name} añadido a {member.display_name}")

@bot.command(name="removerole")
@commands.has_permissions(manage_roles=True)
async def removerole(ctx, member: discord.Member, role: discord.Role):
    if ctx.author.top_role <= role:
        return await ctx.send("❌ No puedes quitar un rol superior al tuyo.")
    await member.remove_roles(role)
    await ctx.send(f"✅ Rol {role.name} removido de {member.display_name}")

# ==============================================================================
# SISTEMA DE ADVERTENCIAS (WARNS - SQLITE)
# ==============================================================================

@bot.command(name="warn")
@commands.has_permissions(kick_members=True)
async def warn(ctx, member: discord.Member, *, reason="Sin razón"):
    timestamp = str(datetime.datetime.now())
    async with aiosqlite.connect("bot_database.db") as db:
        await db.execute(
            "INSERT INTO warns (user_id, guild_id, moderator_id, reason, timestamp) VALUES (?, ?, ?, ?, ?)",
            (member.id, ctx.guild.id, ctx.author.id, reason, timestamp)
        )
        await db.commit()
    
    await ctx.send(embed=create_embed("⚠️ Usuario Advertido", f"**Usuario:** {member.mention}\n**Razón:** {reason}", discord.Color.gold()))

@bot.command(name="warns")
async def warns(ctx, member: discord.Member):
    async with aiosqlite.connect("bot_database.db") as db:
        async with db.execute("SELECT warn_id, moderator_id, reason, timestamp FROM warns WHERE user_id = ? AND guild_id = ?", (member.id, ctx.guild.id)) as cursor:
            rows = await cursor.fetchall()
            
    if not rows:
        return await ctx.send("✅ Este usuario no tiene advertencias.")
    
    desc = ""
    for row in rows:
        mod = ctx.guild.get_member(row[1])
        mod_name = mod.name if mod else "Mod Desconocido"
        desc += f"**ID:** {row[0]} | **Mod:** {mod_name}\n📝 {row[2]}\n📅 {row[3][:19]}\n\n"
    
    embed = create_embed(f"Advertencias de {member.display_name}", desc[:4000], discord.Color.gold())
    await ctx.send(embed=embed)

@bot.command(name="delwarn")
@commands.has_permissions(kick_members=True)
async def delwarn(ctx, warn_id: int):
    async with aiosqlite.connect("bot_database.db") as db:
        await db.execute("DELETE FROM warns WHERE warn_id = ? AND guild_id = ?", (warn_id, ctx.guild.id))
        await db.commit()
    await ctx.send(f"✅ Advertencia ID {warn_id} eliminada.")

@bot.command(name="clearwarns")
@commands.has_permissions(administrator=True)
async def clearwarns(ctx, member: discord.Member):
    async with aiosqlite.connect("bot_database.db") as db:
        await db.execute("DELETE FROM warns WHERE user_id = ? AND guild_id = ?", (member.id, ctx.guild.id))
        await db.commit()
    await ctx.send(f"✅ Todas las advertencias de {member.mention} han sido borradas.")

# ==============================================================================
# UTILIDAD / INFORMACIÓN
# ==============================================================================

# ==============================================================================
# UTILIDAD / INFORMACIÓN
# ==============================================================================

class InviteView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(
            discord.ui.Button(
                label="invite shadow",
                style=discord.ButtonStyle.secondary,  # BOTÓN GRIS
                url="https://discord.com/oauth2/authorize?client_id=1438665735118520371&permissions=8&integration_type=0&scope=bot",
                emoji="🤖"
            )
        )


@bot.command(name="invite")
async def invite(ctx):
    embed = discord.Embed(
        title="Invite shadow",
        description=(
            "Añade **Shadow bot** a tu servidor.\n\n"
            "🔹 Moderación avanzada\n"
            "🔹 Protección\n"
            "🔹 Sistemas inteligentes\n\n"
            "Pulsa el botón de abajo 👇"
        ),
        color=discord.Color.dark_grey()
    )

    if bot.user.avatar:
        embed.set_thumbnail(url=bot.user.avatar.url)

    embed.set_footer(text="Ultimate Mod Bot • Invite System")
    await ctx.send(embed=embed, view=InviteView())


@bot.command(name="snipe")
async def snipe(ctx):
    data = bot.sniped_messages.get(ctx.channel.id)
    if not data:
        return await ctx.send("❌ No hay nada que snipear aquí.")

    embed = discord.Embed(
        description=data["content"],
        color=discord.Color.purple(),
        timestamp=data["time"]
    )
    embed.set_author(
        name=f"{data['author']} borró esto:",
        icon_url=data['author'].avatar.url
    )
    await ctx.send(embed=embed)


@bot.command(name="editsnipe")
async def editsnipe(ctx):
    data = bot.editsniped_messages.get(ctx.channel.id)
    if not data:
        return await ctx.send("❌ No hay mensajes editados recientemente.")

    embed = discord.Embed(color=discord.Color.blue())
    embed.set_author(
        name=f"{data['author']} editó esto:",
        icon_url=data['author'].avatar.url
    )
    embed.add_field(name="Antes", value=data["before"], inline=False)
    embed.add_field(name="Después", value=data["after"], inline=False)
    await ctx.send(embed=embed)


@bot.command(name="userinfo", aliases=["ui", "whois"])
async def userinfo(ctx, member: discord.Member = None):
    member = member or ctx.author
    roles = [role.mention for role in member.roles if role.name != "@everyone"]

    embed = discord.Embed(
        title=f"Info de {member}",
        color=member.color
    )
    embed.set_thumbnail(
        url=member.avatar.url if member.avatar else member.default_avatar.url
    )
    embed.add_field(name="ID", value=member.id)
    embed.add_field(
        name="Cuenta Creada",
        value=member.created_at.strftime("%d/%m/%Y")
    )
    embed.add_field(
        name="Se unió al Server",
        value=member.joined_at.strftime("%d/%m/%Y")
    )
    embed.add_field(
        name=f"Roles ({len(roles)})",
        value=", ".join(roles) if roles else "Ninguno",
        inline=False
    )
    await ctx.send(embed=embed)


@bot.command(name="serverinfo", aliases=["si"])
async def serverinfo(ctx):
    guild = ctx.guild
    embed = discord.Embed(
        title=guild.name,
        color=discord.Color.green()
    )
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)

    embed.add_field(name="Dueño", value=guild.owner)
    embed.add_field(name="Miembros", value=guild.member_count)
    embed.add_field(name="Canales", value=len(guild.channels))
    embed.add_field(name="Roles", value=len(guild.roles))
    embed.add_field(name="Nivel de Boost", value=guild.premium_tier)
    embed.add_field(
        name="Creado el",
        value=guild.created_at.strftime("%d/%m/%Y")
    )
    await ctx.send(embed=embed)


@bot.command(name="avatar", aliases=["av"])
async def avatar(ctx, member: discord.Member = None):
    member = member or ctx.author
    embed = discord.Embed(title=f"Avatar de {member}")
    embed.set_image(
        url=member.avatar.url if member.avatar else member.default_avatar.url
    )
    await ctx.send(embed=embed)


@bot.command(name="ping")
async def ping(ctx):
    await ctx.send(f"🏓 Pong! Latencia: {round(bot.latency * 1000)}ms")


@bot.command(name="uptime")
async def uptime(ctx):
    delta = datetime.datetime.now() - bot.start_time
    hours, remainder = divmod(int(delta.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)
    await ctx.send(f"⏱️ En línea por: {hours}h {minutes}m {seconds}s")

# ==============================================================================
# COMANDOS DE DIVERSIÓN Y MISC
# ==============================================================================

@bot.command(name="8ball")
async def eightball(ctx, *, question):
    responses = ["Sí", "No", "Tal vez", "Definitivamente", "No lo creo", "Pregunta de nuevo", "Claro que sí"]
    await ctx.send(f"🎱 **Pregunta:** {question}\n**Respuesta:** {random.choice(responses)}")

@bot.command(name="coinflip")
async def coinflip(ctx):
    result = random.choice(["Cara", "Cruz"])
    await ctx.send(f"🪙 Ha salido: **{result}**")

@bot.command(name="dice")
async def dice(ctx):
    await ctx.send(f"🎲 Sacaste un: **{random.randint(1, 6)}**")

@bot.command(name="say")
@commands.has_permissions(manage_messages=True)
async def say(ctx, *, message):
    await ctx.message.delete()
import discord
from discord.ext import commands, tasks
import aiosqlite
import aiohttp
import asyncio
import datetime
import random
import io
from itertools import cycle

# --- CONFIGURACIÓN ---
TOKEN = "TU_TOKEN_AQUI"
PREFIX = "$"

# --- INTENTS ---
intents = discord.Intents.all()
intents.members = True
intents.message_content = True

class HyperBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=PREFIX,
            intents=intents,
            help_command=None,
            case_insensitive=True
        )
        self.start_time = datetime.datetime.now()
        self.afk_users = {} # Cache en memoria para rapidez

    async def setup_hook(self):
        await self.init_db()
        await self.add_cog(Moderation(self))
        await self.add_cog(Utility(self))
        await self.add_cog(FunAndSocial(self))
        await self.add_cog(Economy(self))
        print("✅ | TODOS LOS SISTEMAS CARGADOS")

    async def init_db(self):
        async with aiosqlite.connect("hyper_public.db") as db:
            await db.execute("CREATE TABLE IF NOT EXISTS economy (user_id INTEGER PRIMARY KEY, money INTEGER DEFAULT 0, bank INTEGER DEFAULT 0)")
            await db.commit()

    async def on_ready(self):
        print(f"🌐 | LOGUEADO COMO: {self.user}")
        if not self.status_task.is_running():
            self.status_task.start()

    @tasks.loop(seconds=4)
    async def status_task(self):
        stats = [
            f"Sirviendo a {len(self.guilds)} servidores",
            "Moderación Avanzada",
            f"Usuarios: {sum(g.member_count for g in self.guilds)}",
            "$help | By Infinito"
        ]
        await self.change_presence(activity=discord.Game(name=random.choice(stats)))

    # Evento AFK Global
    async def on_message(self, message):
        if message.author.bot: return
        
        # Si el usuario vuelve
        if message.author.id in self.afk_users:
            del self.afk_users[message.author.id]
            await message.channel.send(f"👋 {message.author.mention}, bienvenido de nuevo. Tu AFK ha sido removido.", delete_after=5)

        # Si mencionan a un AFK
        if message.mentions:
            for mention in message.mentions:
                if mention.id in self.afk_users:
                    reason = self.afk_users[mention.id]
                    embed = discord.Embed(description=f"💤 **{mention.name}** está AFK: {reason}", color=discord.Color.dark_gray())
                    await message.channel.send(embed=embed, delete_after=8)
        
        await self.process_commands(message)

bot = HyperBot()

# --- HELPER VISUAL ---
def create_embed(title, desc, color=0x5865F2, img=None, thumb=None):
    embed = discord.Embed(title=title, description=desc, color=color, timestamp=datetime.datetime.now())
    if img: embed.set_image(url=img)
    if thumb: embed.set_thumbnail(url=thumb)
    embed.set_footer(text="Hyper System Public", icon_url=bot.user.avatar.url if bot.user.avatar else None)
    return embed

# ==============================================================================
# 🛡️ COG 1: MODERACIÓN DE ALTO NIVEL (ADMINISTRADORES)
# ==============================================================================
class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def massrole(self, ctx, role: discord.Role, target: str = "humans"):
        """
        Da un rol a TODOS. 
        Uso: $massrole @Rol humans (o bots/all)
        """
        if ctx.author.top_role <= role:
            return await ctx.send("❌ El rol es superior a ti.")
        
        await ctx.send(f"🔄 Iniciando asignación masiva de **{role.name}** a **{target}**. Esto tomará tiempo...")
        count = 0
        members = ctx.guild.members
        
        for member in members:
            if target == "bots" and not member.bot: continue
            if target == "humans" and member.bot: continue
            
            if role not in member.roles:
                try:
                    await member.add_roles(role)
                    count += 1
                    await asyncio.sleep(0.5) # Evitar Rate Limit
                except:
                    pass
        
        await ctx.send(f"✅ Operación finalizada. Rol añadido a **{count}** miembros.")

    @commands.command()
    @commands.has_permissions(ban_members=True)
    async def hackban(self, ctx, user_id: int, *, reason="Hackban por seguridad"):
        """Banea a alguien que NO está en el servidor."""
        try:
            user = await self.bot.fetch_user(user_id)
            await ctx.guild.ban(user, reason=reason)
            await ctx.send(embed=create_embed("🛡️ HACKBAN", f"El usuario **{user.name}** (`{user_id}`) ha sido baneado preventivamente.", discord.Color.red()))
        except:
            await ctx.send("❌ Usuario no encontrado o error de permisos.")

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def purge(self, ctx, amount: int, filtro: str = None):
        """
        $purge 100
        $purge 50 bots (Solo borra bots)
        $purge 50 images (Solo borra imágenes)
        """
        def check(m):
            if filtro == "bots": return m.author.bot
            if filtro == "images": return len(m.attachments) > 0
            return True

        deleted = await ctx.channel.purge(limit=amount, check=check)
        await ctx.send(f"🧹 Eliminados **{len(deleted)}** mensajes.", delete_after=3)

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def lockdown(self, ctx, channel: discord.TextChannel = None):
        """Cierra el canal actual o uno mencionado."""
        channel = channel or ctx.channel
        await channel.set_permissions(ctx.guild.default_role, send_messages=False)
        await ctx.send(embed=create_embed("🔒 LOCKDOWN", f"El canal {channel.mention} ha sido cerrado.", discord.Color.dark_red()))

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def unlock(self, ctx, channel: discord.TextChannel = None):
        """Abre un canal cerrado."""
        channel = channel or ctx.channel
        await channel.set_permissions(ctx.guild.default_role, send_messages=True)
        await ctx.send(embed=create_embed("🔓 UNLOCK", f"El canal {channel.mention} está abierto.", discord.Color.green()))

    @commands.command()
    @commands.has_permissions(manage_channels=True)
    async def nuke(self, ctx):
        """Clona y destruye el canal para limpiarlo al 100%."""
        embed = create_embed("☢️ NUKE TÁCTICO", "Detonación en 3 segundos...", discord.Color.orange())
        await ctx.send(embed=embed)
        await asyncio.sleep(3)
        new_ch = await ctx.channel.clone(reason="Nuke Command")
        await ctx.channel.delete()
        await new_ch.send(embed=create_embed("☢️ LIMPIEZA COMPLETADA", "Canal reconstruido exitosamente.", discord.Color.green()))

# ==============================================================================
# 🛠️ COG 2: UTILIDAD & HERRAMIENTAS (LO NUEVO)
# ==============================================================================
class Utility(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.has_permissions(manage_emojis=True)
    async def steal(self, ctx, emoji: discord.PartialEmoji, nombre: str = None):
        """Roba un emoji de otro servidor y lo agrega al tuyo."""
        if not nombre: nombre = emoji.name
        
        async with aiohttp.ClientSession() as session:
            async with session.get(emoji.url) as resp:
                if resp.status != 200: return await ctx.send("❌ Error al descargar imagen.")
                data = await resp.read()
        
        try:
            new_emoji = await ctx.guild.create_custom_emoji(name=nombre, image=data)
            await ctx.send(embed=create_embed("😜 Emoji Robado", f"He añadido {new_emoji} con el nombre **{nombre}**.", discord.Color.green()))
        except Exception as e:
            await ctx.send(f"❌ Error (Quizás no quedan huecos): {e}")

    @commands.command()
    async def imitate(self, ctx, member: discord.Member, *, mensaje):
        """Crea un webhook y habla como si fueras otro usuario."""
        if not ctx.channel.permissions_for(ctx.me).manage_webhooks:
            return await ctx.send("❌ Necesito permiso de `Gestionar Webhooks`.")
        
        webhook = await ctx.channel.create_webhook(name=member.display_name)
        await ctx.message.delete()
        
        await webhook.send(
            str(mensaje), 
            username=member.display_name, 
            avatar_url=member.display_avatar.url
        )
        await asyncio.sleep(5)
        await webhook.delete() # Borrar para no ensuciar

    @commands.command()
    async def afk(self, ctx, *, reason="AFK"):
        """Ponte en modo Ausente."""
        self.bot.afk_users[ctx.author.id] = reason
        await ctx.send(f"💤 **{ctx.author.name}**, te he puesto en AFK. Razón: {reason}")

    @commands.command()
    async def banner(self, ctx, member: discord.Member = None):
        """Consigue el banner de un usuario (Nitro o Color)."""
        member = member or ctx.author
        user = await self.bot.fetch_user(member.id)
        if user.banner:
            await ctx.send(embed=create_embed(f"Banner de {user.name}", "", img=user.banner.url))
        else:
            await ctx.send("❌ Este usuario no tiene banner, usa un color sólido.")

    @commands.command()
    async def jumbo(self, ctx, emoji: discord.PartialEmoji):
        """Muestra un emoji en tamaño gigante."""
        await ctx.send(embed=create_embed("JUMBO", "", img=emoji.url))

    @commands.command()
    async def wiki(self, ctx, *, busqueda):
        """Busca algo rápido en Wikipedia (Link directo)."""
        url = f"https://es.wikipedia.org/wiki/{busqueda.replace(' ', '_')}"
        await ctx.send(embed=create_embed(f"📚 Wikipedia: {busqueda}", f"[Click para leer el artículo]({url})", discord.Color.light_grey()))

    @commands.command()
    async def calc(self, ctx, *, operacion):
        """Calculadora científica básica."""
        allowed = set("0123456789+-*/.() ")
        if set(operacion).issubset(allowed):
            try:
                res = eval(operacion)
                await ctx.send(embed=create_embed("🧮 Calculadora", f"`{operacion}` = **{res}**", discord.Color.blurple()))
            except:
                await ctx.send("❌ Error de sintaxis.")
        else:
            await ctx.send("❌ Caracteres no permitidos.")

# ==============================================================================
# 🎉 COG 3: DIVERSIÓN Y SOCIAL
# ==============================================================================
class FunAndSocial(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def meme(self, ctx):
        """Obtiene un meme aleatorio de Reddit."""
        async with aiohttp.ClientSession() as cs:
            async with cs.get('https://meme-api.com/gimme') as r:
                res = await r.json()
                if 'url' in res:
                    embed = create_embed(res['title'], "", discord.Color.random(), img=res['url'])
                    await ctx.send(embed=embed)
                else:
                    await ctx.send("❌ No encontré memes hoy.")

    @commands.command()
    async def ship(self, ctx, user1: discord.Member, user2: discord.Member = None):
        """Calculadora de amor."""
        user2 = user2 or ctx.author
        percent = random.randint(0, 100)
        bar = "█" * (percent // 10) + "░" * (10 - (percent // 10))
        msg = f"💗 **{percent}%** de compatibilidad\n`[{bar}]`"
        
        if percent > 80: msg += "\n🔥 ¡Son almas gemelas!"
        elif percent < 20: msg += "\n🥶 Mejor ni lo intenten..."
        
        await ctx.send(embed=create_embed(f"💘 {user1.name} x {user2.name}", msg, discord.Color.pink()))

    @commands.command()
    async def hack(self, ctx, member: discord.Member):
        """Simula hackear a un usuario (Broma)."""
        msg = await ctx.send(f"💻 Injecting malware to {member.name}...")
        await asyncio.sleep(2)
        await msg.edit(content="🔓 Bypassing firewall 2FA...")
        await asyncio.sleep(2)
        await msg.edit(content="📂 Downloading `homework_folder.zip`...")
        await asyncio.sleep(2)
        await msg.edit(content="📧 Finding IP address...")
        await asyncio.sleep(2)
        await msg.edit(content=f"✅ **HACK COMPLETADO**\nIP: 192.168.1.{random.randint(0,255)}\nEmail: {member.name}@gmail.com\nPass: iloveminecraft123")

    @commands.command()
    async def firstmsg(self, ctx):
        """Te lleva al primer mensaje del canal."""
        msg = [m async for m in ctx.channel.history(limit=1, oldest_first=True)][0]
        await ctx.send(embed=create_embed("📜 Primer Mensaje", f"[Click para viajar al pasado]({msg.jump_url})", discord.Color.gold()))

# ==============================================================================
# 💰 COG 4: ECONOMÍA BÁSICA
# ==============================================================================
class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def get_bal(self, user_id):
        async with aiosqlite.connect("hyper_public.db") as db:
            cursor = await db.execute("SELECT money, bank FROM economy WHERE user_id=?", (user_id,))
            row = await cursor.fetchone()
            if not row:
                await db.execute("INSERT INTO economy (user_id) VALUES (?)", (user_id,))
                await db.commit()
                return 0, 0
            return row[0], row[1]

    async def add_money(self, user_id, amount, is_bank=False):
        async with aiosqlite.connect("hyper_public.db") as db:
            col = "bank" if is_bank else "money"
            await self.get_bal(user_id) # Asegurar registro
            await db.execute(f"UPDATE economy SET {col} = {col} + ? WHERE user_id = ?", (amount, user_id))
            await db.commit()

    @commands.command(aliases=["bal"])
    async def balance(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        money, bank = await self.get_bal(member.id)
        embed = create_embed(f"💳 Finanzas de {member.name}", f"💵 **Efectivo:** ${money}\n🏦 **Banco:** ${bank}\n💰 **Total:** ${money+bank}", discord.Color.green())
        await ctx.send(embed=embed)

    @commands.command()
    @commands.cooldown(1, 600, commands.BucketType.user)
    async def work(self, ctx):
        earnings = random.randint(50, 300)
        jobs = ["Programador", "Streamer", "Cajero", "Abogado", "Hacker"]
        await self.add_money(ctx.author.id, earnings)
        await ctx.send(f"💼 Trabajaste como **{random.choice(jobs)}** y ganaste **${earnings}**.")

    @commands.command()
    @commands.cooldown(1, 1200, commands.BucketType.user)
    async def crime(self, ctx):
        if random.choice([True, False]):
            earnings = random.randint(300, 800)
            await self.add_money(ctx.author.id, earnings)
            await ctx.send(f"😈 Robaste un banco y ganaste **${earnings}**.")
        else:
            loss = random.randint(100, 300)
            await self.add_money(ctx.author.id, -loss)
            await ctx.send(f"🚓 Te atrapó la policía. Pagaste **${loss}** de fianza.")

# --- MANEJO DE ERRORES ---
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ **Acceso Denegado:** No tienes permisos suficientes.")
    elif isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"⏳ **Cooldown:** Espera {round(error.retry_after)} segundos.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("⚠️ **Faltan datos:** Revisa cómo usas el comando.")
    elif isinstance(error, commands.BotMissingPermissions):
        await ctx.send("❌ **Error:** No tengo permisos para hacer eso.")
    else:
        print(f"Error: {error}")

if __name__ == "__main__":
    bot.run(TOKEN)
