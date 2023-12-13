import asyncio
import aiomysql

from payments.config.manager import Config 
from payments.utils.common import *
from payments.service.goods import Good
from payments.utils.placeholder import *
from payments.service.user import *
from payments.service.ticket import *

table_name = "plefest_users"
tickets_table_name = "plefest_tickets"

def isEmpty(something: any) -> bool:
    return something == {} or something == [] or something == None or something == ()

class Database:
    def __init__(self, settings: dict) -> None:
        self.connection = None
        if "port" not in settings:
            settings["port"] = 3306
        self.settings = settings
    
    async def create_ticket(self, inter: disnake.ModalInteraction, config: Config, good: Good) -> Ticket:
        """
        Создает и сохраняет тикет (везде)
        """
        # User Data
        user = inter.user
        account = await self.get_user(user.id)
        if account.balance < good.cost:
            return None
        
        account.balance -= good.cost
        await self.save_user(account)

        # Channel Creating
        guild_id = config.data["guild"]
        guild = inter.bot.get_guild(guild_id)

        category_id = config.data["tickets"]["category"]
        category = disnake.utils.get(guild.categories, id=category_id)

        title = f"{good.name}-{str(get_seconds())[3:]}"
        channel = await guild.create_text_channel(title, category=category, overwrites={
            guild.default_role: disnake.PermissionOverwrite(view_channel=False)
        })

        # Instance
        ticket = construct_ticket(channel.id, user.id, good.name, balance=good.cost)

        # Saving
        query = f"INSERT INTO {tickets_table_name} (buyer, good, balance, worker, active, channel_id) VALUES (%s, %s, %s, %s, %s, %s)"
        cursor = await self.connection.cursor()
        await cursor.execute(query, ticket.to_tuple())
        await cursor.close()

        # Placeholders
        w_plh = ticket.get_placeholders() | good.get_placeholders()
        for key, value in inter.text_values.items():
            w_plh = w_plh | {
                f"%field:{key}%": value
            }
        
        # Channel Messages
        buy_data_embed = placeholder_embed_dict(good.good_dict["buy_data_embed"], user, account, w_plh)
        embed = placeholder_embed_dict(good.good_dict["ticket_embed"], user, account, w_plh)
        buttons = []
        for key, value in config.data["tickets"]["buttons"].items():
            cid = f"aniby:ticket_action:{key}"
            buttons.append(
                disnake.ui.Button(
                    label=value["label"],
                    style=disnake.ButtonStyle[value["style"]],
                    custom_id=cid
                )
            )
        await channel.send(embeds=[embed, buy_data_embed], components=buttons)

        # Worker Channel
        worker_channel = inter.bot.get_channel(config.data["worker_channel"])

        w_dict = config.data["tickets"]["messages"]["worker"]
        
        w_content, w_embeds = format_response(w_dict, user, account, additional_placeholders=w_plh)
        w_embeds.append(buy_data_embed)
        w_bd = w_dict["accept_button"]
        w_button = disnake.ui.Button(
            label=w_bd["label"],
            style=disnake.ButtonStyle[w_bd["style"]],
            custom_id="aniby:accept_ticket:" + str(ticket.channel_id)
        )
        
        await worker_channel.send(content=w_content, embeds=w_embeds, components=[w_button])

        return ticket
    
    async def close_ticket(self, ticket: Ticket, bot: Bot = None, comission: int = 0, reason: str | None = None) -> tuple | None:
        """
        Закрывает тикет, делает инактивным в базе\n
        Баланс тикета переходит к рабочему
        """
        # Discord
        result = await ticket.close(bot, reason)
        if result:
            # Worker Database
            worker_account = None
            old_balance = 0
            if ticket.worker != None:
                worker_account = await self.get_user(ticket.worker)
                old_balance = worker_account.balance
                worker_account.balance += ticket.balance * (1 - comission / 100)
                await self.save_user(worker_account)

            # Ticket Database
            ticket._active = False
            await self.save_ticket(ticket)
            return (worker_account, old_balance)
        return None
    
    async def fill_user_list(self) -> None:
        """
        Заполняет список пользователей
        """
        global user_list, table_name
        user_list = []
        
        cursor = await self.connection.cursor()
        await cursor.execute(f"SELECT * FROM {table_name}")
        results = await cursor.fetchmany()
        await cursor.close()

        for res in results:
            construct_user_from_database(res)

        await cursor.close()
    
    async def fill_ticket_list(self) -> None:
        """
        Заполняет список тикетов
        """
        global ticket_list, tickets_table_name
        ticket_list = []
        
        cursor = await self.connection.cursor()
        await cursor.execute(f"SELECT * FROM {tickets_table_name} WHERE active = 1")
        results = await cursor.fetchall()
        await cursor.close()

        for res in results:
            construct_ticket_from_database(res)

        await cursor.close()
    
    async def async_init(self) -> None:
        self._loop = asyncio.get_event_loop()
        self.connection = await aiomysql.connect(
            host=self.settings["host"],
            port=self.settings["port"],
            user=self.settings["user"],
            password=self.settings["password"],
            db=self.settings["database"],
            autocommit=True,
            loop=self._loop
        )
        
        # cursor = await self.connection.cursor()
        # check_query = f"SELECT * FROM information_schema.tables WHERE table_name LIKE '{table_name}'"
        # await cursor.execute(check_query)
        # result = await cursor.fetchone()
        # await cursor.close()
        
        # if result == None:
        create_users = f"CREATE TABLE IF NOT EXISTS `{table_name}` (`id` INT NOT NULL AUTO_INCREMENT, `discord` TEXT NOT NULL, `balance` INT NOT NULL DEFAULT 0, PRIMARY KEY (`id`));"
        create_tickets = f"CREATE TABLE IF NOT EXISTS `{tickets_table_name}` (`id` INT NOT NULL AUTO_INCREMENT, `channel_id` TEXT NOT NULL, `buyer` TEXT NOT NULL, `good` TEXT NOT NULL, `balance` INT NOT NULL DEFAULT 0, `worker` TEXT DEFAULT NULL, `active` BOOLEAN NOT NULL DEFAULT 1, PRIMARY KEY (`id`));"
        cursor = await self.connection.cursor()
        await cursor.execute(create_users)
        await cursor.execute(create_tickets)
        await cursor.close()
        
        await self.fill_user_list()
        await self.fill_ticket_list()
    
    async def delete_ticket(self, channel_id: str) -> None:
        global tickets_table_name
        query = f"DELETE FROM {tickets_table_name} WHERE channel_id = %s"
        
        cursor = await self.connection.cursor()
        await cursor.execute(query, (channel_id))
        await cursor.close()
        
        remove_ticket(channel_id)
    
    async def save_ticket(self, ticket: Ticket) -> None:
        global tickets_table_name
        
        query = f"UPDATE {tickets_table_name} SET buyer = %s, good = %s, balance = %s, worker = %s, active = %s WHERE channel_id = %s" 
        
        replace_ticket(ticket)
        
        cursor = await self.connection.cursor()
        await cursor.execute(query, (ticket.buyer, ticket.good, ticket.balance, ticket.worker, ticket._active, str(ticket.channel_id)))
        await cursor.close()
    
    async def get_ticket(self, channel_id: str) -> Ticket:
        ticket = get_ticket(channel_id)
        if ticket != None:
            return ticket
        
        global tickets_table_name
        cursor = await self.connection.cursor()
        await cursor.execute(f"SELECT * FROM {tickets_table_name} WHERE channel_id = '{channel_id}';")
        result = await cursor.fetchone()
        await cursor.close()
        
        if not isEmpty(result):
            return construct_ticket_from_database(result)
        return None
    
    async def save_user(self, user: PlefestUser) -> None:
        cursor = await self.connection.cursor()
        await cursor.execute(f"SELECT * FROM {table_name} WHERE discord = '{user.discord}'")
        result = await cursor.fetchone()
        await cursor.close()
        
        cursor = await self.connection.cursor()
        query = f"INSERT INTO {table_name} (discord, balance) VALUES ('{user.discord}', {user.balance});" if isEmpty(result) else f"UPDATE {table_name} SET balance = {user.balance} WHERE discord = '{user.discord}';"
        await cursor.execute(query)
        await cursor.close()
        
        replace_user(user)
    
    async def get_user(self, discord: str | int) -> PlefestUser:
        if isinstance(discord, int):
            discord = str(discord)
        
        user = get_user(discord)
        if user != None:
            return user
        
        global table_name
        
        cursor = await self.connection.cursor()
        await cursor.execute(f"SELECT * FROM {table_name} WHERE discord = '{discord}';")
        result = await cursor.fetchone()
        await cursor.close()
        
        if not isEmpty(result):
            return construct_user_from_database(result)
        return construct_user(discord, 0)
    
    def disconnect(self):
        self.connection.close()
        self._loop = None
        self.connection = None