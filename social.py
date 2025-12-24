import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont
import io
import functools

class Social(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def generate_rank_card(self, username, avatar_bytes, level, xp, xp_needed):
        # Esta función corre en otro hilo para no congelar el bot
        width, height = 800, 200
        bg_color = (35, 39, 42)
        
        image = Image.new("RGB", (width, height), bg_color)
        draw = ImageDraw.Draw(image)
        
        # Avatar
        if avatar_bytes:
            avatar_img = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA").resize((150, 150))
            mask = Image.new("L", (150, 150), 0)
            ImageDraw.Draw(mask).ellipse((0, 0, 150, 150), fill=255)
            image.paste(avatar_img, (25, 25), mask)

        # Texto (Usamos default font para evitar errores de archivos faltantes)
        # En prod: ImageFont.truetype("arial.ttf", 40)
        draw.text((200, 50), f"Usuario: {username}", fill="white", font_size=40)
        draw.text((200, 100), f"Nivel: {level}", fill="#5865F2", font_size=30)
        draw.text((400, 100), f"XP: {xp} / {xp_needed}", fill="gray", font_size=30)
        
        # Barra
        draw.rectangle([200, 150, 750, 170], fill=(60, 60, 60))
        fill = int((xp / xp_needed) * 550)
        if fill > 0:
            draw.rectangle([200, 150, 200 + fill, 170], fill="#5865F2")
            
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        buffer.seek(0)
        return buffer

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild: return
        
        # Lógica de XP
        async with self.bot.db.execute("SELECT xp, level FROM users WHERE user_id = ? AND guild_id = ?", (message.author.id, message.guild.id)) as cursor:
            row = await cursor.fetchone()
            if not row:
                await self.bot.db.execute("INSERT INTO users (user_id, guild_id, xp, level) VALUES (?, ?, 0, 1)", (message.author.id, message.guild.id))
                xp, level = 0, 1
            else:
                xp, level = row

        xp += 5
        xp_needed = 5 * (level ** 2) + 50 * level + 100
        
        if xp >= xp_needed:
            level += 1
            xp = 0
            await message.channel.send(f"🎉 {message.author.mention} ha subido al **Nivel {level}**!")

        await self.bot.db.execute("UPDATE users SET xp = ?, level = ? WHERE user_id = ? AND guild_id = ?", (xp, level, message.author.id, message.guild.id))
        await self.bot.db.commit()

    @commands.hybrid_command(name="rank", description="Muestra tu tarjeta de nivel.")
    async def rank(self, ctx, usuario: discord.Member = None):
        usuario = usuario or ctx.author
        await ctx.defer()
        
        async with self.bot.db.execute("SELECT xp, level FROM users WHERE user_id = ? AND guild_id = ?", (usuario.id, ctx.guild.id)) as cursor:
            row = await cursor.fetchone()
            xp, level = row if row else (0, 1)

        xp_needed = 5 * (level ** 2) + 50 * level + 100
        avatar_bytes = await usuario.display_avatar.read()

        # Ejecutar generación de imagen en Executor (Anti-Lag)
        fn = functools.partial(self.generate_rank_card, usuario.name, avatar_bytes, level, xp, xp_needed)
        buffer = await self.bot.loop.run_in_executor(None, fn)
        
        file = discord.File(buffer, filename="rank.png")
        await ctx.send(file=file)

async def setup(bot):
    await bot.add_cog(Social(bot))
