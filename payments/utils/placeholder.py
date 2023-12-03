from copy import deepcopy
import time, disnake

from payments.service.user import PlefestUser

def replace_text_with_dict(text: str, obj: dict):
    for key, value in obj.items():
        value = value if isinstance(value, str) else str(value)
        text = text.replace(key, value)
    return text

def placeholder(source_text: str, user: disnake.User | None = None, account: PlefestUser | None = None, additional_placeholders: dict | None = None) -> str:
    text = deepcopy(source_text)
    if additional_placeholders != None:
        text = replace_text_with_dict(text, additional_placeholders)
    if user != None:
        text = text.replace("%name%", user.name)
    if account != None:
        text = replace_text_with_dict(text, account.get_placeholders())
    return text

def placeholder_embed_dict(source_embed: dict, user: disnake.User | None = None, account: PlefestUser | None = None, additional_placeholders: dict | None = None) -> disnake.Embed:
    embed = deepcopy(source_embed)
    if "title" in embed:
        embed["title"] = placeholder(embed["title"], user, account, additional_placeholders)[:256]
    
    if "description" in embed:
        embed["description"] = placeholder(embed["description"], user, account, additional_placeholders)[:4096]
    
    if "author" in embed and "name" in embed["author"]:
        embed["author"]["name"] = placeholder(embed["author"]["name"], user, account, additional_placeholders)[:256]
        
    if "footer" in embed and "text" in embed["footer"]:
        embed["footer"]["text"] = placeholder(embed["footer"]["text"], user, account, additional_placeholders)[:2048]

    if "fields" in embed:
        new_fields = []
        for field in embed["fields"]:
            field["name"] = placeholder(field["name"], user, account, additional_placeholders)[:256]
            field["value"] = placeholder(field["value"], user, account, additional_placeholders)[:1024]
            new_fields.append(field)
        embed["fields"] = new_fields
    return disnake.Embed.from_dict(embed)

def format_response(obj: dict, user: disnake.User | None = None, account: dict | None = None, additional_placeholders: dict | None = None):
    content = placeholder(obj["content"], user, account, additional_placeholders) if "content" in obj else None
    embeds = []
    if "embeds" in obj:
        for ej in obj["embeds"]:
            embeds.append(placeholder_embed_dict(ej, user, account, additional_placeholders))
    
    return (content, embeds)

async def return_message(message: dict, inter: disnake.ApplicationCommandInteraction, user: disnake.User | None = None, account: PlefestUser | None = None, additional_placeholders: dict | None = None, components = None):
    content, embeds = format_response(obj=message, user=user, account=account, additional_placeholders=additional_placeholders)
    await inter.edit_original_response(content=content, embeds=embeds, components=components)

def time_milliseconds():
    return round(time.time() * 1000)