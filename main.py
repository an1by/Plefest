import disnake
from disnake.ext import commands

bot = commands.InteractionBot()


@bot.event
async def on_ready():
    bot.tree.clear_commands(guild=None)
    await bot.tree.sync()
    print("Бот готов!")

bot.load_extension("payments.cog")
bot.run("MTEyMDM1NTcwMzc2NTM1MjUzOQ.GTeP87.KiK9cojk9ku5c2n-MeHUHSTq7GnIQO83PraAVo")