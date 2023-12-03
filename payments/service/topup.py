import disnake
from disnake import TextInputStyle

from payments.config.manager import Config
from payments.service.client import Client
from payments.utils.placeholder import return_message, format_response
from payments.utils.common import get_milliseconds

class TopupModal(disnake.ui.Modal):
    def __init__(self, config: Config, ym: Client):
        self._config = config
        self._ym = ym
        data = config.data["commands"]["account"]["topup"]["modal"]
        
        components = [
            disnake.ui.TextInput(
                label=data["input"]["label"],
                placeholder=data["input"]["placeholder"],
                custom_id="aniby:topup:amount",
                style=TextInputStyle.short,
                max_length=10
            )
        ]
        super().__init__(title=data["title"], custom_id="aniby:topup", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        await inter.response.defer(ephemeral=True)
        
        user = inter.user
        
        amount = inter.text_values["aniby:topup:amount"]
        try:
            amount = int(amount)
        except:
            return_message(self._config.data["other_messages"]["invalid_argument"], inter, user)
            return
        link = self._ym.createPayment(user.id, "Покупка монет", "Покупка монет", ("aniby:topup:" + str(get_milliseconds())), amount).replace(" ", "%20")
        
        main_object = self._config.data["commands"]["account"]["topup"]["created"]
        await return_message(main_object, inter, user, components=[
            disnake.ui.Button(
                label=main_object["url_button"]["label"],
                url=link
            ),
            disnake.ui.Button(
                label=main_object["check_button"]["label"],
                style=disnake.ButtonStyle[main_object["check_button"]["style"]],
                custom_id="aniby:topup:check"
            )
        ])
        