import discord
from discord.ext import commands
import os
import time
import openai
from datetime import timedelta

# ================= CONFIG =================
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")

openai.api_key = OPENAI_KEY

PREFIX = "!"
LOG_CHANNEL = "logs"

intents = discord.Intents.all()
bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)

# ================= DATA =================
spam_control = {}
warnings = {}
antilink = True

# ================= READY =================
@bot.event
async def on_ready():
    print(f"✅ Conectado como {bot.user}")

# ================= LOGS =================
async def log(guild, msg):
    for c in guild.text_channels:
        if c.name == LOG_CHANNEL:
            await c.send(msg)
            break

# ================= IA =================
async def ai_response(prompt):
    try:
        r = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Eres una IA moderadora profesional estilo JAR"},
                {"role": "user", "content": prompt}
            ]
        )
        return r.choices[0].message.content
    except:
        return "⚠️ Error con la IA."

# ================= AUTOMOD =================
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    uid = message.author.id
    now = time.time()

    # Anti-link
    if antilink and ("http://" in message.content or "https://" in message.content):
        if not message.author.guild_permissions.manage_messages:
            await message.delete()
            await message.channel.send(f"🚫 {message.author.mention} links no permitidos")
            await log(message.guild, f"🚫 Link borrado de {message.author}")
            return

    # Anti-spam
    spam_control.setdefault(uid, [])
    spam_control[uid].append(now)
    spam_control[uid] = [t for t in spam_control[uid] if now - t < 5]

    if len(spam_control[uid]) > 6:
        await message.delete()
        await message.channel.send(f"⚠️ {message.author.mention} spam detectado")
        return

    await bot.process_commands(message)

# ================= HELP PRO =================
@bot.command()
async def help(ctx, categoria=None):
    embed = discord.Embed(
        title="🤖 Panel de Comandos PRO",
        description="Bot de moderación estilo JAR + IA",
        color=0x2F3136
    )

    if categoria == "mod" or categoria is None:
        embed.add_field(
            name="🛡️ Moderación",
            value="""
`!ban @user razón`
`!kick @user razón`
`!mute @user min`
`!unmute @user`
`!warn @user razón`
`!warnings @user`
`!clear cantidad`
`!lock`
`!unlock`
`!slowmode segundos`
            """,
            inline=False
        )

    if categoria == "ia" or categoria is None:
        embed.add_field(
            name="🤖 IA",
            value="""
`!ia pregunta`
`!ask pregunta`
`!analizar texto`
            """,
            inline=False
        )

    if categoria == "util" or categoria is None:
        embed.add_field(
            name="⚙️ Utilidades",
            value="""
`!ping`
`!info`
`!avatar @user`
`!say texto`
            """,
            inline=False
        )

    if categoria == "seguridad" or categoria is None:
        embed.add_field(
            name="🔐 Seguridad",
            value="""
`!antilink on/off`
`!lock`
`!unlock`
            """,
            inline=False
        )

    embed.set_footer(text="Ej: !help mod | !help ia | Sistema PRO")
    await ctx.send(embed=embed)

# ================= MODERACIÓN =================
@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int):
    await ctx.channel.purge(limit=amount + 1)
    await ctx.send(f"🧹 {amount} mensajes borrados", delete_after=5)

@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason="Sin razón"):
    await member.kick(reason=reason)
    await ctx.send(f"👢 {member} expulsado")

@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason="Sin razón"):
    await member.ban(reason=reason)
    await ctx.send(f"🔨 {member} baneado")

@bot.command()
@commands.has_permissions(moderate_members=True)
async def mute(ctx, member: discord.Member, minutes: int):
    until = discord.utils.utcnow() + timedelta(minutes=minutes)
    await member.timeout(until)
    await ctx.send(f"🔇 {member} muteado {minutes} min")

@bot.command()
@commands.has_permissions(moderate_members=True)
async def unmute(ctx, member: discord.Member):
    await member.timeout(None)
    await ctx.send(f"🔊 {member} desmuteado")

# ================= WARNS =================
@bot.command()
@commands.has_permissions(moderate_members=True)
async def warn(ctx, member: discord.Member, *, reason="Sin razón"):
    warnings.setdefault(member.id, [])
    warnings[member.id].append(reason)

    await ctx.send(f"⚠️ {member.mention} advertido | {reason}")

    if len(warnings[member.id]) >= 3:
        await member.timeout(discord.utils.utcnow() + timedelta(minutes=10))
        await ctx.send(f"🔇 {member.mention} mute automático (3 warns)")

@bot.command()
async def warnings(ctx, member: discord.Member):
    w = warnings.get(member.id, [])
    if not w:
        await ctx.send("✅ Sin advertencias")
    else:
        await ctx.send("⚠️ Advertencias:\n" + "\n".join(w))

# ================= SEGURIDAD =================
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
@commands.has_permissions(manage_guild=True)
async def antilink(ctx, estado):
    global antilink
    if estado.lower() == "on":
        antilink = True
        await ctx.send("✅ Anti-link activado")
    elif estado.lower() == "off":
        antilink = False
        await ctx.send("❌ Anti-link desactivado")

# ================= IA =================
@bot.command()
async def ia(ctx, *, pregunta):
    msg = await ctx.send("🤖 Pensando...")
    r = await ai_response(pregunta)
    await msg.edit(content=r)

@bot.command()
async def ask(ctx, *, pregunta):
    r = await ai_response(f"Responde como bot profesional de Discord: {pregunta}")
    await ctx.send(r)

@bot.command()
async def analizar(ctx, *, texto):
    r = await ai_response(f"Analiza este mensaje y di si rompe reglas: {texto}")
    await ctx.send(r)

# ================= UTIL =================
@bot.command()
async def ping(ctx):
    await ctx.send(f"🏓 {round(bot.latency * 1000)}ms")

@bot.command()
async def info(ctx):
    await ctx.send(f"🤖 En {len(bot.guilds)} servidores")

@bot.command()
async def avatar(ctx, member: discord.Member = None):
    member = member or ctx.author
    await ctx.send(member.avatar.url)

@bot.command()
@commands.has_permissions(administrator=True)
async def say(ctx, *, texto):
    await ctx.message.delete()
    await ctx.send(texto)

# ================= ERRORES =================
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ No tienes permisos")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("⚠️ Argumentos incompletos")
    else:
        print(error)

# ================= START =================
bot.run(TOKEN)
