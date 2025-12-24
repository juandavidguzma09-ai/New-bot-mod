import discord
from discord.ext import commands
import datetime
import asyncio
import aiosqlite
import random
import io
import os

TOKEN = os.getenv("TOKEN")
DEFAULT_PREFIX = "!"

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
                    prefix TEXT DEFAULT '!',
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
    await bot.change_presence(activity=discord.Game(name=f"Protegiendo {len(bot.guilds)} servidores | !help"))

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
    embed.set_footer(text="Ultimate Mod Bot")
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

class InviteView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(
            discord.ui.Button(
                label="Invitar Ultimate Bot",
                style=discord.ButtonStyle.secondary,  # BOTÓN GRIS
                url="https://discord.com/oauth2/authorize?client_id=1438665735118520371&permissions=8&integration_type=0&scope=bot",
                emoji="🤖"
            )
        )

@bot.command(name="invite")
async def invite(ctx):
    embed = discord.Embed(
        title="Invita Ultimate Mod Bot",
        description=(
            "Añade **Ultimate Mod Bot** a tu servidor.\n\n"
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
    
    embed = discord.Embed(description=data["content"], color=discord.Color.purple(), timestamp=data["time"])
    embed.set_author(name=f"{data['author']} borró esto:", icon_url=data['author'].avatar.url)
    await ctx.send(embed=embed)

@bot.command(name="editsnipe")
async def editsnipe(ctx):
    data = bot.editsniped_messages.get(ctx.channel.id)
    if not data:
        return await ctx.send("❌ No hay mensajes editados recientemente.")
    
    embed = discord.Embed(color=discord.Color.blue())
    embed.set_author(name=f"{data['author']} editó esto:", icon_url=data['author'].avatar.url)
    embed.add_field(name="Antes", value=data["before"], inline=False)
    embed.add_field(name="Después", value=data["after"], inline=False)
    await ctx.send(embed=embed)

@bot.command(name="userinfo", aliases=["ui", "whois"])
async def userinfo(ctx, member: discord.Member = None):
    member = member or ctx.author
    roles = [role.mention for role in member.roles if role.name != "@everyone"]
    
    embed = discord.Embed(title=f"Info de {member}", color=member.color)
    embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
    embed.add_field(name="ID", value=member.id)
    embed.add_field(name="Cuenta Creada", value=member.created_at.strftime("%d/%m/%Y"))
    embed.add_field(name="Se unió al Server", value=member.joined_at.strftime("%d/%m/%Y"))
    embed.add_field(name=f"Roles ({len(roles)})", value=", ".join(roles) if roles else "Ninguno", inline=False)
    await ctx.send(embed=embed)

@bot.command(name="serverinfo", aliases=["si"])
async def serverinfo(ctx):
    guild = ctx.guild
    embed = discord.Embed(title=guild.name, color=discord.Color.green())
    if guild.icon: embed.set_thumbnail(url=guild.icon.url)
    embed.add_field(name="Dueño", value=guild.owner)
    embed.add_field(name="Miembros", value=guild.member_count)
    embed.add_field(name="Canales", value=len(guild.channels))
    embed.add_field(name="Roles", value=len(guild.roles))
    embed.add_field(name="Nivel de Boost", value=guild.premium_tier)
    embed.add_field(name="Creado el", value=guild.created_at.strftime("%d/%m/%Y"))
    await ctx.send(embed=embed)

@bot.command(name="avatar", aliases=["av"])
async def avatar(ctx, member: discord.Member = None):
    member = member or ctx.author
    embed = discord.Embed(title=f"Avatar de {member}")
    embed.set_image(url=member.avatar.url if member.avatar else member.default_avatar.url)
    await ctx.send(embed=embed)

@bot.command(name="ping")
async def ping(ctx):
    await ctx.send(f"🏓 Pong! Latencia: {round(bot.latency * 1000)}ms")

@bot.command(name="uptime")
async def uptime(ctx):
    delta_uptime = datetime.datetime.now() - bot.start_time
    hours, remainder = divmod(int(delta_uptime.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)
    await ctx.send(f"⏱️ En línea por: {hours}h {minutes}m {seconds}s")

# ==============================================================================
# CONFIGURACIÓN DEL BOT
# ==============================================================================

@bot.command(name="setprefix")
@commands.has_permissions(administrator=True)
async def setprefix(ctx, new_prefix: str):
    async with aiosqlite.connect("bot_database.db") as db:
        await db.execute("INSERT OR REPLACE INTO guilds (guild_id, prefix) VALUES (?, ?)", (ctx.guild.id, new_prefix))
        await db.commit()
    await ctx.send(f"✅ Prefijo actualizado a `{new_prefix}`")

@bot.command(name="setlog")
@commands.has_permissions(administrator=True)
async def setlog(ctx, channel: discord.TextChannel):
    async with aiosqlite.connect("bot_database.db") as db:
        await db.execute("UPDATE guilds SET log_channel = ? WHERE guild_id = ?", (channel.id, ctx.guild.id))
        # Si no existe la fila, insertarla (puede pasar si no cambiaron prefix)
        await db.execute("INSERT OR IGNORE INTO guilds (guild_id, log_channel) VALUES (?, ?)", (ctx.guild.id, channel.id))
        await db.commit()
    await ctx.send(f"✅ Canal de logs establecido en {channel.mention}")

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
    await ctx.send(message)

@bot.command(name="embed")
@commands.has_permissions(manage_messages=True)
async def embed_cmd(ctx, title, *, description):
    # Uso: !embed "Titulo entre comillas" Descripción del embed
    embed = create_embed(title, description)
    await ctx.send(embed=embed)

@bot.command(name="poll")
async def poll(ctx, question, *options):
    if len(options) < 2:
        return await ctx.send("Necesitas al menos 2 opciones. Uso: `!poll \"Pregunta\" \"Opción 1\" \"Opción 2\"`")
    if len(options) > 10:
        return await ctx.send("Máximo 10 opciones.")
    
    reactions = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    description = []
    for x, option in enumerate(options):
        description.append(f"\n {reactions[x]} {option}")
        
    embed = discord.Embed(title=question, description="".join(description), color=discord.Color.gold())
    msg = await ctx.send(embed=embed)
    for i in range(len(options)):
        await msg.add_reaction(reactions[i])

@bot.command(name="choose")
async def choose(ctx, *choices):
    if not choices: return await ctx.send("Dame opciones.")
    await ctx.send(f"🤔 Yo elijo: **{random.choice(choices)}**")

@bot.command(name="reverse")
async def reverse(ctx, *, text: str):
    await ctx.send(text[::-1])

@bot.command(name="ship")
async def ship(ctx, member1: discord.Member, member2: discord.Member):
    percent = random.randint(0, 100)
    emoji = "💔" if percent < 30 else "🧡" if percent < 70 else "💖"
    bar = "█" * (percent // 10) + "░" * (10 - (percent // 10))
    embed = discord.Embed(title=f"Ship: {member1.name} x {member2.name}", description=f"{percent}% {emoji}\n[{bar}]", color=discord.Color.pink())
    await ctx.send(embed=embed)

# ==============================================================================
# AYUDA PERSONALIZADA
# ==============================================================================

@bot.command(name="help")
async def help_cmd(ctx):
    embed = discord.Embed(title="Menú de Ayuda", description=f"Prefijo actual: `{await bot.get_prefix(ctx.message)}`", color=discord.Color.blurple())
    
    moderation = "`ban`, `kick`, `softban`, `timeout`, `unmute`, `purge`, `nuke`, `lock`, `unlock`, `slowmode`, `addrole`, `removerole`"
    warns = "`warn`, `, `delwarn`, `clearwarns`"
    utility = "`snipe`, `editsnipe`, `userinfo`, `serverinfo`, `avatar`, `ping`, `uptime`"
    config = "`setprefix`, `setlog`"
    fun = "`8ball`, `coinflip`, `dice`, `say`, `embed`, `poll`, `choose`, `reverse`, `ship`"
    
    embed.add_field(name="👮 Moderación", value=moderation, inline=False)
    embed.add_field(name="⚠️ Advertencias", value=warns, inline=False)
    embed.add_field(name="🛠️ Utilidad", value=utility, inline=False)
    embed.add_field(name="⚙️ Configuración", value=config, inline=False)
    embed.add_field(name="🎲 Diversión", value=fun, inline=False)
    
    embed.set_footer(text="Usa !comando para ejecutar.")
    await ctx.send(embed=embed)

# ==============================================================================
# MANEJO DE ERRORES (ERROR HANDLING)
# ==============================================================================

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return # Ignorar comandos inexistentes
    
    if isinstance(error, commands.MissingPermissions):
        perms = ", ".join(error.missing_permissions)
        await ctx.send(f"❌ **Acceso denegado.** Te faltan permisos: `{perms}`")
    
    elif isinstance(error, commands.BotMissingPermissions):
        perms = ", ".join(error.missing_permissions)
        await ctx.send(f"❌ **No puedo hacer eso.** Me faltan permisos: `{perms}`")
    
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ **Faltan argumentos.** Uso correcto: `{ctx.prefix}{ctx.command.name} {ctx.command.signature}`")
    
    elif isinstance(error, commands.MemberNotFound):
        await ctx.send("❌ No pude encontrar a ese miembro.")
    
    elif isinstance(error, commands.BadArgument):
        await ctx.send("❌ Argumento inválido. Verifica si escribiste bien el número o mencionaste al usuario.")
    
    elif isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"⏳ Espera {round(error.retry_after, 1)}s antes de usar este comando.")
    
    else:
        print(f"Error en comando {ctx.command}: {error}")
        await ctx.send("❌ Ocurrió un error inesperado. Revisa la consola si eres el dueño.")

# ==============================================================================
# EJECUCIÓN
# ==============================================================================

if __name__ == "__main__":
    try:
        bot.run(TOKEN)
    except Exception as e:
        print(f"Error al iniciar el bot: {e}")
        print("Asegúrate de haber puesto el TOKEN correcto y tener activados los INTENTS en Discord Developer Portal.")
