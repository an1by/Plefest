import disnake
from disnake.ext import commands
from disnake import TextInputStyle


class mod1(disnake.ui.Modal):
    def __init__(self):
        components = [
            disnake.ui.TextInput(
                label="Ваш ник",
                placeholder="Игровой никнейм из майнкрафта",
                custom_id="> ник",
                style=TextInputStyle.short,
                max_length=15,
            ),
            disnake.ui.TextInput(
                label="Есть пк?",
                placeholder="Если нету то не пишите заявку",
                custom_id="> пк",
                style=TextInputStyle.short,
                max_length=3,
            ),
            disnake.ui.TextInput(
                label="Готовы взять ответственность?",
                placeholder="В случае игнора требований = бан.",
                custom_id="> ответ",
                style=TextInputStyle.short,
                max_length=10,
            ),
        ]
        super().__init__(
            title="Заявка",
            custom_id="create_tag",
            components=components,
            timeout=900.0,
        )

    async def callback(self, inter: disnake.ModalInteraction):
        embed = disnake.Embed(title="ЗАЯВКА", color=0xffe662)
        embed.add_field(name="> Никнейм", value="```" + inter.text_values['> ник'] + "```", inline=False)
        embed.add_field(name="> Пк", value="```" + inter.text_values['> пк'] + "```", inline=True)
        embed.add_field(name="> Условия", value="```" + inter.text_values['> ответ'] + "```", inline=True)
        embed.add_field(name="", value=f"{inter.user.mention}", inline=False)
        channel = inter.bot.get_channel(1180831863720398909)
        embed2 = disnake.Embed(title="УСПЕШНО", color=0xffe662)
        await channel.send(embed=embed)
        await inter.response.send_message(embed=embed2, ephemeral=True)


class m1(disnake.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @disnake.ui.button(label="Заявка", style=disnake.ButtonStyle.secondary, url=None, emoji=None, disabled=False, custom_id="button2")
    async def button2(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        await inter.response.send_modal(modal=mod1())


class ButtonsCog2(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.persistent_views_added = False

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.persistent_views_added:
            self.bot.add_view(m1())
            self.persistent_views_added = True

    @commands.slash_command(name="заявка", description="да")
    async def help(self, interaction):
        view = m1()
        embed = disnake.Embed(title="ЗАЯВКА", color=0x00ff00)
        embed.set_thumbnail(url=self.bot.user.avatar.url)
        embed.add_field(name="", value="```Нажмите на кнопку, чтобы подать заявку```", inline=False)
        channel = self.bot.get_channel(1180831863720398909)
        await channel.send(embed=embed, view=view)
        embed2 = disnake.Embed(title="УСПЕШНО", color=0xffe662)
        await interaction.response.send_message(embed=embed2, ephemeral=True)


def setup(bot):
    bot.add_cog(ButtonsCog2(bot))