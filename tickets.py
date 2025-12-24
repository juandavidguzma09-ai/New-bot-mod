import discord
from discord.ext import commands
from discord import ui

class TicketView(ui.View):
    def __init__(self):
        super().__init__(timeout=None) # Persistente

    @ui.button(label="Crear Ticket", style=discord.ButtonStyle.blurple, emoji="📩", custom_id="ticket_create")
    async def create_ticket(self, interaction: discord.Interaction, button: ui.Button):
        channel_name = f"ticket-{interaction.user.name.lower()}"
        guild = interaction.guild
        
        # Permisos
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True)
        }
        
        channel = await guild.create_text_channel(channel_name, overwrites=overwrites)
        
        embed = discord.Embed(title="Ticket Abierto", description=f"Hola {interaction.user.mention}, describe tu problema.", color=0x5865F2)
        await channel.send(embed=embed, view=CloseView())
        await interaction.response.send_message(f"✅ Ticket creado: {channel.mention}", ephemeral=True)

class CloseView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="Cerrar", style=discord.ButtonStyle.red, emoji="🔒", custom_id="ticket_close")
    async def close_ticket(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_message("Cerrando ticket en 5 segundos...")
        await asyncio.sleep(5)
        await interaction.channel.delete()

class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def setup_tickets(self, ctx):
        """Envía el panel de tickets."""
        await ctx.message.delete()
        embed = discord.Embed(title="Centro de Soporte", description="Pulsa el botón para abrir un ticket privado.", color=0x2ECC71)
        # Añadimos la view. Para que sea persistente tras reinicio, deberías añadirla en on_ready en main.py también
        await ctx.send(embed=embed, view=TicketView())

    @commands.Cog.listener()
    async def on_ready(self):
        # Registrar la vista para que funcione tras reiniciar
        self.bot.add_view(TicketView())
        self.bot.add_view(CloseView())

async def setup(bot):
    await bot.add_cog(Tickets(bot))
