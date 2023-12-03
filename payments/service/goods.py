import disnake

from payments.config.manager import Config
from payments.service.client import Client
from payments.service.ticket import *
import payments.utils.placeholder as placeholders


class GoodBuyModal(disnake.ui.Modal):
    def __init__(self, good, config: Config, ym: Client, database):
        self._config = config
        self._good = good
        self._ym = ym
        self._db = database

        modal = self._good.good_dict["modal"]

        components = []
        for obj in modal["components"]:
            components.append(
                disnake.ui.TextInput(
                    label=obj["label"],
                    placeholder=obj["placeholder"],
                    required=obj["required"],
                    style=disnake.TextInputStyle[obj["style"]],
                    custom_id=obj["custom_id"],
                )
            )

        super().__init__(
            title=modal["title"],
            custom_id=f"aniby:buy_good:{self._good.name}",
            components=components,
        )

    async def callback(self, inter: disnake.ModalInteraction):
        await inter.response.defer(ephemeral=True)
        
        account = await self._db.get_user(inter.user.id)
        if self._good.cost > account.balance:
            er_c, er_e = placeholders.format_response(
                self._config.data["other_messages"]["no_money"], inter.user, account, self._good.get_placeholders()
            )
            await inter.followup.send(content=er_c, embeds=er_e, ephemeral=True)
            return

        ticket = await self._db.create_ticket(inter, self._config, self._good)
        
        await placeholders.return_message(
            (
                self._config.data["tickets"]["messages"]["created"]
                if ticket != None
                else self._config.data["other_messages"]["no_money"]
            ),
            inter, additional_placeholders=ticket.get_placeholders()
        )


class Good(object):
    def __init__(self, name: str, good_dict: dict) -> None:
        self.name = name
        self.good_dict = good_dict

        self.cost = good_dict["cost"]
        button_data = good_dict["button"]
        self._button = disnake.ui.Button(
            label=button_data["label"],
            style=disnake.ButtonStyle[button_data["style"]],
            custom_id=("aniby:buy_good:" + name),
        )

        plh = self.get_placeholders()
        self._embed = placeholders.placeholder_embed_dict(
            good_dict["embed"], additional_placeholders=plh
        )
        self._ticket_embed = placeholders.placeholder_embed_dict(
            good_dict["ticket_embed"], additional_placeholders=plh
        )

    def get_placeholders(self):
        return {
            "%good_key%": self.name,
            "%good_name%": self.good_dict["name"],
            "%good_cost%": (int(self.cost * 100) / 100),
        }

    def get_modal(self, config: Config, yoomoney: Client, database) -> GoodBuyModal:
        return GoodBuyModal(self, config, yoomoney, database)
