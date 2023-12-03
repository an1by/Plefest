from datetime import datetime

def get_milliseconds():
    return int(datetime.now().timestamp() * 1000)

def get_seconds() -> int:
    return round(datetime.now().timestamp())

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

bot_prefix = "[Plefest Payments]"