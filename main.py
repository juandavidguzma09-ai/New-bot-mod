import discord
from discord.ext import commands
import os
import time
import openai

# ========= CONFIG =========
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")

openai.api_key = OPENAI_KEY

PREFIX = "!"
LOG_CHANNEL = "logs"

intents = discord.Intents.all()
bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)

spam_control = {}

# ========= READY =========
@bot.event
async def on_ready():
    print(f"✅ Bot conectado como {bot.user}")

# ========= LOGS =========
async def log(guild, msg):
    for c in guild.text_channels:
        if c.name == LOG_CHANNEL:
            await c.send(msg)
            break

# ========= IA =========
async def ai_response(prompt):
    try:
        r = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Eres una IA moderadora experta para Discord"},
                {"role": "user", "content": prompt}
            ]
        )
        return r.choices[0].message.content
    except:
        return "⚠️ Error con la IA."

# ========= ANTI SPAM =========
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    uid = message.author.id
    now = time.time()

    spam_control.setdefault(uid, [])
    spam_control[uid].append(now)
    spam_control[uid] = [t for t in spam_control[uid] if now - t < 5]

    if len(spam_control[uid]) > 6:
        await message.delete()
        await message.channel.send(f"🚫 {message.author.mention} deja de spamear.")
        return

    await bot.process_commands(message)

# ========= HELP ESTILO JAR =========
@bot.command()
async def help(ctx):
    embed = discord.Embed(
        title="🤖 Panel de Comandos",
        description="Bot de moderación profesional con IA integrada",
        color=0x2F3136
    )

    embed.add_field(
        name="🛡️ Moderación",
        value="""
`!ban @user razón`
`!kick @user razón`
`!mute @user minutos`
`!unmute @user`
`!clear cantidad`
        """,
        inline=False
    )

    embed.add_field(
        name="🤖 Inteligencia Artificial",
        value="""
`!ia pregunta`
`!analizar texto`
        """,
        inline=False
    )

    embed.add_field(
        name="⚙️ Utilidades",
        value="""
`!ping`
`!info`
        """,
        inline=False
    )

    embed.set_footer(text="Sistema tipo JAR • Seguridad avanzada")
    await ctx.send(embed=embed)

# ========= COMANDOS MOD =========
@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int):
    await ctx.channel.purge(limit=amount+1)
    await ctx.send(f"🧹 {amount} mensajes borrados", delete_after=5)
    await log(ctx.guild, f"🧹 {ctx.author} limpió {amount}")

@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason="Sin razón"):
    await member.kick(reason=reason)
    await ctx.send(f"👢 {member} expulsado")
    await log(ctx.guild, f"👢 {member} kick | {reason}")

@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason="Sin razón"):
    await member.ban(reason=reason)
    await ctx.send(f"🔨 {member} baneado")
    await log(ctx.guild, f"🔨 {member} ban | {reason}")

@bot.command()
@commands.has_permissions(moderate_members=True)
async def mute(ctx, member: discord.Member, minutes: int):
    until = discord.utils.utcnow() + discord.timedelta(minutes=minutes)
    await member.timeout(until)
    await ctx.send(f"🔇 {member} muteado {minutes} min")

@bot.command()
@commands.has_permissions(moderate_members=True)
async def unmute(ctx, member: discord.Member):
    await member.timeout(None)
    await ctx.send(f"🔊 {member} desmuteado")

# ========= IA COMMANDS =========
@bot.command()
async def ia(ctx, *, pregunta):
    msg = await ctx.send("🤖 Pensando...")
    respuesta = await ai_response(pregunta)
    await msg.edit(content=respuesta)

@bot.command()
async def analizar(ctx, *, texto):
    r = await ai_response(f"Analiza este texto y dime si rompe reglas: {texto}")
    await ctx.send(r)

# ========= UTIL =========
@bot.command()
async def ping(ctx):
    await ctx.send(f"🏓 Pong: {round(bot.latency*1000)}ms")

@bot.command()
async def info(ctx):
    await ctx.send(f"🤖 Bot activo en {len(bot.guilds)} servidores")

# ========= ERRORES =========
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ No tienes permisos.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("⚠️ Argumentos incompletos.")
    else:
        print(error)

# ========= START =========
bot.run(TOKEN)
