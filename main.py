import disnake
from disnake.ext import commands

bot = commands.InteractionBot()


@bot.event
async def on_ready():
    bot.tree.clear_commands(guild=None)
    await bot.tree.sync()
    print("Бот готов!")

bot.load_extension("payments.cog")
bot.run("MTEyMDM1NTcwMzc2NTM1MjUzOQ.G9-2Up.6ND6hcR3tCLX2fK6xKZpciPnCnkeJUYHF65mX0")