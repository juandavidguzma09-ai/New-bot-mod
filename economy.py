import discord
from discord.ext import commands, tasks
import random

class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def get_balance(self, user_id, guild_id):
        async with self.bot.db.execute("SELECT wallet, bank FROM users WHERE user_id = ? AND guild_id = ?", (user_id, guild_id)) as cursor:
            row = await cursor.fetchone()
            if not row:
                await self.bot.db.execute("INSERT INTO users (user_id, guild_id) VALUES (?, ?)", (user_id, guild_id))
                await self.bot.db.commit()
                return 0, 0
            return row

    async def update_wallet(self, user_id, guild_id, amount):
        await self.bot.db.execute("INSERT OR IGNORE INTO users (user_id, guild_id) VALUES (?, ?)", (user_id, guild_id))
        await self.bot.db.execute("UPDATE users SET wallet = wallet + ? WHERE user_id = ? AND guild_id = ?", (amount, user_id, guild_id))
        await self.bot.db.commit()

    @commands.hybrid_command(name="work", description="Trabaja y gana dinero.")
    @commands.cooldown(1, 3600, commands.BucketType.user)
    async def work(self, ctx):
        earnings = random.randint(50, 300)
        await self.update_wallet(ctx.author.id, ctx.guild.id, earnings)
        
        embed = discord.Embed(title="💼 Trabajo Completo", description=f"Trabajaste duro y ganaste **${earnings}**.", color=0xF1C40F)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="balance", description="Mira tu dinero.")
    async def balance(self, ctx, user: discord.Member = None):
        user = user or ctx.author
        wallet, bank = await self.get_balance(user.id, ctx.guild.id)
        
        embed = discord.Embed(title=f"Billetera de {user.name}", color=0x5865F2)
        embed.add_field(name="💵 Efectivo", value=f"${wallet}", inline=True)
        embed.add_field(name="💳 Banco", value=f"${bank}", inline=True)
        embed.add_field(name="💎 Total", value=f"${wallet + bank}", inline=False)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="deposit", description="Deposita dinero en el banco.")
    async def deposit(self, ctx, cantidad: str):
        wallet, bank = await self.get_balance(ctx.author.id, ctx.guild.id)
        
        if cantidad.lower() == "all":
            amount = wallet
        else:
            try: amount = int(cantidad)
            except: return await ctx.send("❌ Cantidad inválida.")

        if amount > wallet or amount <= 0:
            return await ctx.send("❌ No tienes suficiente dinero.")

        await self.bot.db.execute("UPDATE users SET wallet = wallet - ?, bank = bank + ? WHERE user_id = ? AND guild_id = ?", (amount, amount, ctx.author.id, ctx.guild.id))
        await self.bot.db.commit()
        
        await ctx.send(f"✅ Has depositado **${amount}** en tu banco.")

async def setup(bot):
    await bot.add_cog(Economy(bot))
