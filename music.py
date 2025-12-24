import discord
from discord.ext import commands
import yt_dlp
import asyncio

# Opciones optimizadas
YDL_OPTIONS = {'format': 'bestaudio/best', 'noplaylist': True, 'quiet': True, 'default_search': 'auto'}
FFMPEG_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.queues = {}

    @commands.hybrid_command(name="play", description="Reproduce música de YT.")
    async def play(self, ctx, *, busqueda: str):
        if not ctx.author.voice:
            return await ctx.send("❌ Entra a un canal de voz primero.")
        
        if not ctx.voice_client:
            await ctx.author.voice.channel.connect()
        
        await ctx.defer()
        
        # Extracción en hilo separado
        loop = self.bot.loop
        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            data = await loop.run_in_executor(None, lambda: ydl.extract_info(busqueda, download=False))
        
        if 'entries' in data: data = data['entries'][0]
        url = data['url']
        title = data['title']
        
        # Sistema de Cola simple
        vc = ctx.voice_client
        if vc.is_playing():
            return await ctx.send(f"⚠️ Ya hay música sonando. (Sistema de cola avanzado en V4)")
            
        source = discord.FFmpegPCMAudio(url, **FFMPEG_OPTIONS)
        vc.play(source)
        
        embed = discord.Embed(title="🎶 Reproduciendo", description=f"**{title}**", color=0xE91E63)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="stop", description="Detiene la música.")
    async def stop(self, ctx):
        if ctx.voice_client:
            await ctx.voice_client.disconnect()
            await ctx.send("🛑 Desconectado.")

async def setup(bot):
    await bot.add_cog(Music(bot))
