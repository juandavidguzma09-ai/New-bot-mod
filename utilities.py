@app_commands.command(name="userinfo")
async def userinfo(interaction, user: discord.Member):
    await interaction.response.send_message(
        f"👤 {user}\nID: {user.id}\nCreada: {user.created_at}"
    )

@app_commands.command(name="serverinfo")
async def serverinfo(interaction):
    g = interaction.guild
    await interaction.response.send_message(
        f"🏠 {g.name}\nMiembros: {g.member_count}"
    )

@app_commands.command(name="ping")
async def ping(interaction):
    await interaction.response.send_message("🏓 Pong")
