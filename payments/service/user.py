class PlefestUser:
    def __init__(self, discord: str, permission: str, balance: int) -> None:
        self.discord = discord
        self.permission = permission
        self.balance = balance
    
    def permission_name(self):
        permission_name = "Пользователь"
        match (self.permission):
            case "worker":
                permission_name = "Рабочий"
            case "admin":
                permission_name = "Администратор"
        return permission_name
    
    def get_placeholders(self, prefix: str = "account"):
        return {
            f"%{prefix}_discord%": self.discord,
            f"%{prefix}_permission%": self.permission,
            f"%{prefix}_permission_name%": self.permission_name(),
            f"%{prefix}_balance%": (int(self.balance * 100) / 100)
        }

user_list = []

def construct_user(discord: str, permission: str, balance: int) -> PlefestUser:
    global user_list
    user = PlefestUser(discord, permission, balance)
    user_list.append(user)
    return user

def construct_user_from_database(data: tuple) -> PlefestUser:
    global user_list
    _id, discord, permission, balance = data
    user = PlefestUser(discord, permission, balance)
    user_list.append(user)
    return user

def replace_user(user: PlefestUser) -> None:
    global user_list
    for index, local in enumerate(user_list):
        if local.discord == user.discord:
            user_list[index] = user
            return
    user_list.append(user)

def get_user(discord: str) -> PlefestUser | None:
    global user_list
    for user in user_list:
        if user.discord == discord:
            return user
    return None