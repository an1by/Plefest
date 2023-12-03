from disnake.ext.commands.bot import Bot
import disnake

class Ticket:
    def __init__(self, channel_id: str | int, buyer: str | int, good: str, worker: str | None = None, balance: int = 0):
        self.channel_id = int(channel_id) if isinstance(channel_id, str) else channel_id
        self._channel = None
        self.buyer = str(buyer) if isinstance(buyer, int) else buyer
        self.good = good
        self.worker = worker
        self.balance = balance
        self._active = True
    
    async def close(self, bot: Bot, reason: str | None = None) -> bool:
        """
        Закрывает тикет, делает инактивным в базе\n
        Баланс тикета переходит к рабочему
        """
        # Discord
        await self.get_channel(bot).delete(reason=reason)
        
        self._active = False
        
        # Localy
        remove_ticket(self.channel_id)
        return True
    
    def get_channel(self, bot: Bot | None = None) -> disnake.TextChannel | None:
        if self._channel != None:
            return self._channel
        if self._channel == None and bot != None:
            self._channel = bot.get_channel(self.channel_id)
        return self._channel

    def get_placeholders(self):
        return {
            "%ticket_title%": self.title(),
            "%ticket_buyer%": self.buyer,
            "%ticket_channel%": self.channel_id,
            "%ticket_worker%": self.worker,
            "%ticket_good%": self.good,
            "%ticket_worker_mention%": ("Нет" if self.worker == None else f"<@{self.worker}>"),
            "%ticket_balance%": (int(self.balance * 100) / 100)
        }
    
    def to_tuple(self):
        return (self.buyer, self.good, self.balance, self.worker, self._active, self.channel_id)

    def title(self) -> str | None:
        """
        Возвращает номер тикета
        """
        return self._channel.name if self._channel != None else None

ticket_list = []

def construct_ticket_from_database(data: tuple) -> Ticket:
    """
    Добавляет данные тикета в список, возвращая `Ticket` (локально)
    """
    global ticket_list
    _id, channel_id, buyer, good, balance, worker, _active = data
    ticket = Ticket(channel_id, buyer, good, worker, balance)
    ticket_list.append(ticket)
    return ticket

def construct_ticket(channel_id: str | int, buyer: str | int, good: str, worker: str | None = None, balance: int = 0) -> Ticket:
    """
    Добавляет данные тикета в список, возвращая `Ticket` (локально)
    """
    global ticket_list
    ticket = Ticket(channel_id, buyer, good, worker, balance)
    ticket_list.append(ticket)
    return ticket

def replace_ticket(ticket: Ticket) -> None:
    """
    Заменяет данные тикета по его `channel_id` (локально)
    """
    global ticket_list
    for index, local in enumerate(ticket_list):
        if local.channel_id == ticket.channel_id:
            ticket_list[index] = ticket
            return
    ticket_list.append(ticket)

def remove_ticket(channel_id: str) -> Ticket | None:
    global ticket_list
    for index, ticket in enumerate(ticket_list):
        if ticket.channel_id == channel_id:
            ticket_list.pop(index)
            return ticket
    return None

def get_ticket(channel_id: int | str) -> Ticket | None:
    global ticket_list
    if isinstance(channel_id, str):
        channel_id = int(channel_id)
    for ticket in ticket_list:
        if ticket.channel_id == channel_id:
            return ticket
    return None