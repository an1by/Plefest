# https://glqiwiapi.readthedocs.io/en/latest/getting-started/yoomoney/examples.html#examples

from glQiwiApi import YooMoneyAPI
from glQiwiApi.yoo_money.types import AccountInfo
from payments.utils.common import get_seconds

class Payment:
    def __init__(self, title: str, comment: str, custom_id: str, amount: int) -> None:
        self.targets = title
        self.comment = comment
        self.label = custom_id
        self.amount = amount
        self._created_at = get_seconds()
    
    def create(self, receiver: str) -> str:
        """
        Возвращает: Временную ссылку для оплаты
        """
        return YooMoneyAPI.create_pay_form(
            receiver=receiver,
            quick_pay_form="shop", # shop/donate
            targets=self.targets,
            payment_type="SB", # PC/SB
            label=self.label,
            comment=self.comment,
            amount=self.amount
        )
    
    async def check(self, wallet: YooMoneyAPI) -> float:
        if get_seconds() - self._created_at >= 600:
            return -2
        history = await wallet.operation_history()
        for operation in history.operations:
            if operation.status == "success" and operation.label == self.label:
                return operation.amount
        return -1

class Client(object):
    def __init__(self, token: str) -> None:
        self.wallet = YooMoneyAPI(token)
        self.payments = {}
        self.account_number = None
    
    async def info(self) -> AccountInfo:
        async with self.wallet as w:
            return await w.retrieve_account_info()
    
    async def async_init(self):
        self.account_number = (await self.info()).account
    
    async def transferMoney(self, target: str, amount: int, comment: str = None):
        async with self.wallet as w:
            await w.transfer_money(
                to_account=target,
                amount=amount,
                comment=comment
            )
    
    async def checkPayment(self, discord: str | int):
        if isinstance(discord, int):
            discord = str(discord)
        payment = self.getPayment(discord)
        if payment == None:
            return -2
        amount = await payment.check(self.wallet)
        if amount == -2:
            self.removePayment(discord)
        return amount
    
    def createPayment(self, discord: str | int, title: str, comment: str, custom_id: str, amount: int) -> str:
        if isinstance(discord, int):
            discord = str(discord)
        self.payments[discord] = Payment(title, comment, custom_id, amount)
        return self.payments[discord].create(self.account_number)
    
    def getPayment(self, discord: str | int) -> Payment | None:
        if isinstance(discord, int):
            discord = str(discord)
        return self.payments[discord] if discord in self.payments else None
    
    def removePayment(self, discord: str | int) -> None:
        if isinstance(discord, int):
            discord = str(discord)
        del self.payments[discord]
