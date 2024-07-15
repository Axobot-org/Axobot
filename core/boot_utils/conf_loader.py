import json
from typing import TYPE_CHECKING, TypedDict

from cryptography.fernet import Fernet

if TYPE_CHECKING:
    from core.bot_classes import Axobot


class BotInfo(TypedDict):
    "Store the bot token and entity ID, fetched from the database"
    token: str
    entity_id: int

class DatabaseKeys(TypedDict):
    "Store the database connection keys"
    user: str
    password: str
    host: str

class TwitchKeys(TypedDict):
    "Store the client ID and secret for the Twitch API"
    client_id: str
    client_secret: str

class SecretKeys(TypedDict):
    "Map containing all the secret keys used by the bot"
    fernet_key: str
    database: DatabaseKeys
    dbl: str
    bitly: str
    discordbotlist: str
    discordextremelist: str
    statuspage: str
    nasa: str
    random_api_token: str
    google_api: str
    curseforge: str
    twitch: TwitchKeys
    awhikax_api: str

async def load_token(bot: "Axobot", bot_id: int) -> BotInfo:
    "Fetch the bot token from the database, and uncrypt it"
    query = "SELECT `token`, `entity_id` FROM `bot_infos` WHERE `ID` = %s"
    fernet_key = get_secrets_dict()["fernet_key"]
    f = Fernet(fernet_key)
    async with bot.db_main.read(query, (bot_id,), fetchone=True) as result:
        encoded_token = result["token"].encode("utf-8")
        if len(encoded_token) == 0:
            raise ValueError("No token found in database")
        return {
            "token": f.decrypt(encoded_token).decode(),
            "entity_id": result["entity_id"]
        }

def get_secrets_dict() -> SecretKeys:
    "Parse the secrets.json file and return its content"
    with open("secrets.json", "r", encoding="utf-8") as file:
        return json.load(file)
