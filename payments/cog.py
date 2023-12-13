# Disnake
import disnake
from disnake.ext import commands

# Async and Copy
import payments.utils.timeout as timeout
import asyncio, nest_asyncio, multiprocessing
nest_asyncio.apply()
from copy import deepcopy

# Local
from payments.service.user import *
from payments.utils.async_database import Database
import payments.utils.placeholder as placeholders
from payments.config.manager import Config
from payments.service.client import Client as YMClient
from payments.service.topup import TopupModal
from payments.service.goods import Good
from payments.service.surcharge import SurchangeModal
from payments.service.ticket import *
from payments.utils.common import bcolors, bot_prefix

config = Config("payments/config/config.json")
database = None
yoomoney = None

def equalsPermissions(member: disnake.Member, permission_name: str) -> bool:
    perm_dict = config.data["permissions"]
    return member.get_role(perm_dict[permission_name]) != None or member.get_role(perm_dict["admin"]) != None

class Account(commands.Cog):
    def __init__(self, _bot: commands.Bot):
        self.bot = _bot
        self.admin_channel = None
    
    # Admin Functions
    def ready(self) -> bool:
        return database != None and database.connection != None and (not database.connection.closed) and self.admin_channel != None
    
    async def not_ready_message(self, inter: disnake.Interaction) -> bool:
        if not self.ready():
            await inter.response.send_message(content="Бот запускается, подождите еще немного...", ephemeral=True)
            return True
        return False
    
    # Notify
    async def balance_change_notify(self, user: disnake.User, account: PlefestUser, messageable: disnake.TextChannel | disnake.User, balance_before: int, reason: str, additional_placeholders: dict | None = None):
        plh = {
            "%change_balance_before%": balance_before,
            "%change_reason%": reason
        }
        if additional_placeholders != None:
            plh = plh | additional_placeholders
        content, embeds = placeholders.format_response(config.data["other_messages"]["balance_change"], user, account, plh)
        try:
            await messageable.send(content=content, embeds=embeds)
        except:
            pass
    
    # Global init
    async def global_initialization(self):
        # Config
        global config, database, yoomoney
        config.load()
        print(f"{bcolors.OKCYAN}{bot_prefix} Перезагрузил конфиг")
        
        # Yoomoney
        yoomoney = YMClient(config.data["yoomoney_token"])
        await yoomoney.async_init()
        print(f"{bcolors.OKCYAN}{bot_prefix} Инициализировал YooMoney")
        
        # Admin Channel
        self.admin_channel = self.bot.get_channel(config.data["admin_channel"])
        
        # Database
        database = Database(config.data["database"])
        print(f"{bcolors.OKCYAN}{bot_prefix} Подсоединился к базе данных")
        
        await database.async_init()
        print(f"{bcolors.OKCYAN}{bot_prefix} Загрузил пользователей и тикеты")
        
        # Objects
        data = config.data["goods"]
        start_data = data["start"]
        button_data = data["button"]
        goods = data["list"]
        
        # Channel
        channel = self.bot.get_channel(data["channel"])
        await channel.purge(limit=99)
        content, embeds = placeholders.format_response(start_data)
        await channel.send(content=content, embeds=embeds)
        
        for key, value in goods.items():
            button = disnake.ui.Button(
                label=button_data["label"],
                style=disnake.ButtonStyle[button_data["style"]],
                custom_id=("aniby:buy_good:" + key)
            )
            good_oop = Good(key, goods[key])
            w_embeds = [placeholders.placeholder_embed_dict(
                value["embed"], additional_placeholders=good_oop.get_placeholders()
            )]
            await channel.send(embeds=w_embeds, components=[button])
        print(f"{bcolors.OKCYAN}{bot_prefix} Высветил список товаров")
        print(f"{bcolors.OKGREEN}{bot_prefix} Успешно инициализирован!")
    
    def global_disabling(self):
        global ticket_list, user_list, database, yoomoney
        yoomoney = None
        print(f"{bcolors.OKCYAN}{bot_prefix} Отключился от YooMoney")
        
        ticket_list = []
        user_list = []
        self.admin_channel = None
        print(f"{bcolors.OKCYAN}{bot_prefix} Очистил кэш")
        if database != None:
            database.disconnect()
            database = None
        print(f"{bcolors.OKCYAN}{bot_prefix} Отключен от базы данных")
        print(f"{bcolors.OKGREEN}{bot_prefix} Успешно отключен!")
    
    # Surchange Modal Listener
    @commands.Cog.listener()
    async def on_modal_submit(self, inter: disnake.ModalInteraction):
        if not inter.custom_id.startswith("aniby:surchange:"):
            return
        
        ticket = get_ticket(inter.custom_id.replace("aniby:surchange:", ""))
        
        user = inter.user
        
        amount = inter.text_values["aniby:surchange:amount"]
        
        invarg_obj = config.data["other_messages"]["invalid_argument"]
        try:
            amount = float(amount)
        except:
            await placeholders.return_message(invarg_obj, inter, user)
            return
        
        account = await database.get_user(user.id)
        if account.balance < amount or amount <= 0:
            await inter.response.defer(ephemeral=True)
            await placeholders.return_message(invarg_obj, inter, user)
            return
        
        await inter.response.defer()
        
        old_balance = account.balance
        account.balance -= amount
        await database.save_user(account)
        
        # NOTIFY #
        ticket.get_channel(self.bot)
        bc_reason = f"Доплата в заказе <#{ticket.channel_id}> (`{ticket.title()}`)"
        await self.balance_change_notify(user, account, user, old_balance, bc_reason)
        await self.balance_change_notify(user, account, self.admin_channel, old_balance, bc_reason)
        # ===== #
        
        ticket.balance += amount
        await database.save_ticket(ticket)
        
        plh = {"%surchange_amount%": amount} | ticket.get_placeholders()
        await placeholders.return_message(config.data["surchange"]["success"], inter, user, account, plh)
    
    # Global Listeners
    @commands.Cog.listener()
    async def on_ready(self):
        await self.global_initialization()
        
    @commands.Cog.listener
    async def on_resumed(self):
        await self.global_initialization()
    
    @commands.Cog.listener()
    async def on_disconnect(self):
        self.global_disabling()
        
    @commands.Cog.listener("on_button_click")
    async def on_button_click(self, inter: disnake.MessageInteraction):
        if await self.not_ready_message(inter):
            return
        
        cid = inter.component.custom_id
        if not cid.startswith("aniby:"):
            return
        
        user = inter.user
        account = None
        
        cid = cid.replace("aniby:", "", 1)
        
        if not(cid.startswith("ticket_action:surcharge") or cid.startswith("buy_good:")):
            await inter.response.defer(ephemeral=True)
            account = await database.get_user(user.id)
        
        match (cid):
            case "topup:check":
                topup_data = config.data["commands"]["account"]["topup"]
                real_amount = await yoomoney.checkPayment(user.id)
                
                if real_amount == -2:
                    await placeholders.return_message(config.data["other_messages"]["payment_not_found"], inter, user, account)
                    return
                
                if real_amount == -1:
                    check_c, check_e = placeholders.format_response(topup_data["wait"], user, account)
                    await inter.followup.send(content=check_c, embeds=check_e, ephemeral=True)
                    return
                
                plh = {
                    "%topup_real_amount%": real_amount,
                    "%topup_amount%": yoomoney.getPayment(user.id).amount
                }
                
                old_balance = account.balance
                yoomoney.removePayment(user.id)
                account.balance += real_amount
                await database.save_user(account)
                
                # NOTIFY #
                bc_reason = f"Пополнение баланса"
                await self.balance_change_notify(user, account, user, old_balance, bc_reason)
                await self.balance_change_notify(user, account, self.admin_channel, old_balance, bc_reason)
                # ===== #
                
                await placeholders.return_message(topup_data["success"], inter, user, account, plh)
                return
            case _:
                ticket_messages = config.data["tickets"]["messages"]
                if cid.startswith("buy_good:"):
                    good_name = cid.replace("buy_good:", "")
                    good_inst = Good(good_name, config.data["goods"]["list"][good_name])
                    good_modal = good_inst.get_modal(config, yoomoney, database)
                    
                    await inter.response.send_modal(modal=good_modal)
                elif cid.startswith("ticket_action:"):
                    ticket = get_ticket(inter.channel_id)
                    if ticket == None:
                        w_c, w_e = placeholders.format_response(config.data["other_messages"]["error_ticket_interaction"], user, account)
                        await inter.followup.send(content=w_c, embeds=w_e, ephemeral=True)
                        return
                    
                    action = cid.replace("ticket_action:", "")
                    match (action):
                        case "completed":
                            if str(user.id) == str(ticket.buyer) or equalsPermissions(user, "admin"):
                                result = await database.close_ticket(ticket, self.bot, config.data["goods"]["comission"], "Заказ выполнен")
                                if result == None:
                                    return

                                # NOTIFY #
                                worker_account, old_balance = result
                                if worker_account != None:
                                    worker_user = self.bot.get_user(int(worker_account.discord))

                                    bc_reason = f"Выполнение заказа от <@{ticket.buyer}>"
                                    await self.balance_change_notify(worker_user, worker_account, worker_user, old_balance, bc_reason)
                                    await self.balance_change_notify(worker_user, worker_account, self.admin_channel, old_balance, bc_reason)
                                # ===== #

                                worker_channel = inter.bot.get_channel(config.data["worker_channel"])
                                wc_c, wc_e = placeholders.format_response(
                                    ticket_messages["completed"],
                                    user, account,
                                    additional_placeholders=ticket.get_placeholders()
                                )
                                await worker_channel.send(content=wc_c, embeds=wc_e)
                            else:
                                np_content, np_embeds = placeholders.format_response(config.data["other_messages"]["no_permission"], user, account, ticket.get_placeholders())
                                await inter.followup.send(content=np_content, embeds=np_embeds, ephemeral=True)
                        case "surcharge":
                            await inter.response.send_modal(SurchangeModal(ticket, config))
                elif cid.startswith("accept_ticket:"):
                    channel_id = cid.replace("accept_ticket:", "")
                    ticket = get_ticket(channel_id)
                    if ticket == None or ticket.worker != None:
                        a_content, a_embeds = placeholders.format_response(ticket_messages["unavailable"], user, account)
                        await inter.followup.send(content=a_content, embeds=a_embeds, ephemeral=True)
                    else:
                        ticket.worker = user.id
                        await database.save_ticket(ticket)
                        
                        ticket_channel = ticket.get_channel(inter.bot)
                        
                        additional_pl = ticket.get_placeholders() | Good(ticket.good, config.data["goods"]["list"][ticket.good]).get_placeholders()
                        c_content, c_embeds = placeholders.format_response(
                            ticket_messages["taken"]["in_chat"], user, account, additional_pl
                        )
                        await ticket_channel.set_permissions(user,
                            view_channel=True
                        )
                        buyer_user = await ticket_channel.guild.fetch_member(int(ticket.buyer))
                        await ticket_channel.set_permissions(buyer_user,
                            view_channel=True
                        )
                        await ticket_channel.send(content=c_content, embeds=c_embeds)
                        
                        await placeholders.return_message(ticket_messages["worker"], inter, user, account, additional_pl, None)
                return
    
    # Reload command
    @commands.slash_command(description="Перезагрузка бота")
    @commands.has_role(config.data["permissions"]["admin"])
    async def reload(self, inter: disnake.ApplicationCommandInteraction):
        # Error message save
        self._reload_failed = deepcopy(config.data["commands"]["reload"]["error"])
        
        # Messages
        await inter.response.defer(ephemeral=True)
        obj = deepcopy(config.data["commands"]["reload"]["success"])
        print(bcolors.WARNING + "[Plefest Bot] Перезагружаюсь...")
        
        # Main Execution
        self.global_disabling()
        await self.global_initialization()
        
        # Callback
        await placeholders.return_message(obj, inter)
    
    @reload.error
    async def reload_error(self, inter: disnake.ApplicationCommandInteraction, error):
        if isinstance(error, commands.MissingAnyRole):
            await placeholders.return_message(config.data["other_messages"]["no_permission"], inter.user)
            return
            
        await placeholders.return_message(self._reload_failed, inter)
    
    # Pay command
    @commands.slash_command(description="Перевод денег с баланса на аккаунт другого пользователя")
    async def pay(self, inter: disnake.ApplicationCommandInteraction, user: disnake.User = commands.Param(description="Пользователь"), amount: float = commands.Param(description="Сумма в рублях")):
        if await self.not_ready_message(inter):
            return
        
        await inter.response.defer(ephemeral=True)
        
        if user == inter.user:
            await placeholders.return_message(config.data["other_messages"]["invalid_user"], inter)
            return
        
        obj_instance = config.data["commands"]["pay"]
        
        account = await database.get_user(inter.user.id)
        if amount > account.balance or amount <= 0:
            await placeholders.return_message(obj_instance["error"], inter, inter.user, account)
            return
        old_balance = account.balance
        account.balance -= amount
        await database.save_user(account)
        
        # NOTIFY #
        bc_reason = f"Перевод пользователю <@{str(user.id)}> (`{str(user.global_name)}`)"
        await self.balance_change_notify(inter.user, account, inter.user, old_balance, bc_reason)
        await self.balance_change_notify(inter.user, account, self.admin_channel, old_balance, bc_reason)
        # ===== #
        
        target = await database.get_user(user.id)
        old_balance = target.balance
        target.balance += amount
        await database.save_user(target)
        
        # NOTIFY #
        bc_reason = f"Перевод от пользователя <@{str(inter.user.id)}> (`{str(inter.user.global_name)}`)"
        await self.balance_change_notify(user, target, user, old_balance, bc_reason)
        await self.balance_change_notify(user, target, self.admin_channel, old_balance, bc_reason)
        # ===== #
        
        plh = {"%pay_amount%": amount} | target.get_placeholders("target")
        await placeholders.return_message(obj_instance["success"], inter, inter.user, account, plh)
    
    # Account command
    async def help_message(self, inter: disnake.ApplicationCommandInteraction):
        await inter.response.defer(ephemeral=True)
        
        obj = config.data["commands"]["account"]["help"]
        account = await database.get_user(inter.user.id)
        
        await placeholders.return_message(obj, inter, inter.user, account)
    
    @commands.slash_command()
    async def account(self, inter: disnake.ApplicationCommandInteraction):
        if await self.not_ready_message(inter):
            return
    
    @account.sub_command(description="Пополнение баланса аккаунта")
    async def topup(self, inter: disnake.ApplicationCommandInteraction):
        await inter.response.send_modal(TopupModal(config, yoomoney))
    
    async def notify_with_changed_balance(self, inter: disnake.ApplicationCommandInteraction, user: disnake.User, account, old_balance):
         # NOTIFY #
        bc_reason = f"Установлен баланс администратором <@{str(inter.user.id)}>"
        if inter.user.global_name:
            bc_reason += f" (`{inter.user.global_name}`)"
        await self.balance_change_notify(user, account, user, old_balance, bc_reason)
        await self.balance_change_notify(user, account, self.admin_channel, old_balance, bc_reason)
        # ===== #
    
    @account.sub_command(description="Установить баланс аккаунта пользователя")
    @commands.has_role(config.data["permissions"]["admin"])
    async def balance(self, inter: disnake.ApplicationCommandInteraction, user: disnake.User = commands.Param(description="Пользователь"), amount: float = commands.Param(description="Сумма в рублях")):
        await inter.response.defer(ephemeral=False)
        
        account = await database.get_user(user.id)
        old_balance = account.balance
        account.balance = amount
        await database.save_user(account)
        
        try:
            with timeout.time_limit(5):
                await self.notify_with_changed_balance(inter, user, account, old_balance)
        except:
            pass
            
        await placeholders.return_message(config.data["commands"]["account"]["balance"], inter, user=inter.user, account=account)
    @balance.error
    async def balanceError(self, inter, error):
        await inter.edit_original_response(content="Unknown")
        return
    
    @account.sub_command(description="Подсказка к боту")
    async def help(self, inter: disnake.ApplicationCommandInteraction):
        await self.help_message(inter)
    
    def permission_name(self, member: disnake.Member):
        if equalsPermissions(member, "admin"):
            return "Администратор"
        if equalsPermissions(member, "worker"):
            return "Рабочий"
        return "Пользователь"
    
    @account.sub_command(description="Узнать информацию об аккаунте")
    async def info(self, inter: disnake.ApplicationCommandInteraction, user: disnake.User = commands.Param(description="Пользователь", default=None)):
        await inter.response.defer(ephemeral=True)
        
        obj = config.data["commands"]["account"]["info"]
        
        target_user = None
        target_account = None
        
        account = await database.get_user(inter.user.id)
        if (user != None) and (user != target_user):
            if ("permission_other" in obj):
                if not equalsPermissions(inter.user, obj["permission_other"]):
                    await placeholders.return_message(config.data["other_messages"]["no_permission"], inter, inter.user, account, {"%account_permission_name%": self.permission_name(inter.user)})
                    return
            target_user = user
            target_account = await database.get_user(user.id)
        else:
            target_user = inter.user
            target_account = account
        await placeholders.return_message(obj, inter=inter, user=target_user, account=target_account, additional_placeholders={"%account_permission_name%": self.permission_name(target_user)})
    
    @account.sub_command(description="Вывести деньги с баланса аккаунта на счет YooMoney")
    @commands.has_role(config.data["permissions"]["worker"])
    async def withdraw(self, inter: disnake.ApplicationCommandInteraction, yoomoney_requisites: str = commands.Param(description="Номер аккаунта/Номер телефона/Почта", name="yoomoney")):
        await inter.response.defer(ephemeral=True)
        
        obj = config.data["commands"]["account"]["withdraw"]
        user = inter.user;
        account = await database.get_user(user.id)
        
        if account.balance <= 0:
            await placeholders.return_message(config.data["other_messages"]["withdraw_minus"], inter, user, account)
            return
        
        admin_balance = (await yoomoney.info()).balance
        if admin_balance < account.balance:
            await placeholders.return_message(config.data["other_messages"]["no_money_admin"], inter, user, account)
            return
        
        old_balance = account.balance
        account.balance = 0
        await database.save_user(account)
        
        await yoomoney.transferMoney(yoomoney_requisites, old_balance)
        plh = {
            "%withdraw_requisites%": yoomoney_requisites,
            "%withdraw_amount%": old_balance
        }
        
        # NOTIFY #
        bc_reason = f"Ввывод денежных средств на счет YooMoney"
        await self.balance_change_notify(user, account, user, old_balance, bc_reason)
        await self.balance_change_notify(user, account, self.admin_channel, old_balance, bc_reason)
        wtd_c, wtd_e = placeholders.format_response(obj["messages"]["admin"], user, account, plh)
        await self.admin_channel.send(content=wtd_c, embeds=wtd_e)
        # ===== #
        
        await placeholders.return_message(obj["messages"]["success"], inter, user, account, plh)

    @balance.error
    @withdraw.error
    async def permissionError(self, inter, error):
        if isinstance(error, commands.MissingAnyRole):
            await placeholders.return_message(config.data["other_messages"]["no_permission"], inter.user)
            return
        pass

def setup(bot: commands.Bot):
    bot.add_cog(Account(bot))
