import disnake
from disnake import TextInputStyle

from payments.service.ticket import Ticket, get_ticket
from payments.config.manager import Config

class SurchangeModal(disnake.ui.Modal):
    def __init__(self, ticket: Ticket, config: Config):
        self.ticket = ticket
        
        data = config.data["surchange"]["modal"]
        
        components = [
            disnake.ui.TextInput(
                label=data["component"]["label"],
                placeholder=data["component"]["placeholder"],
                custom_id="aniby:surchange:amount",
                style=TextInputStyle.short,
                max_length=10
            )
        ]
        super().__init__(title=data["title"], custom_id="aniby:surchange:" + str(ticket.channel_id), components=components)