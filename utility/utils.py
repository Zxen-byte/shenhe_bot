import re
from datetime import datetime

import discord
import genshin
import yaml
import json

from utility.stat_emojis import stat_emojis


class GetName():
    def __init__(self) -> None:
        with open(f"GenshinData/EN_simple_textMap.yaml", "r") as file:
            self.en = yaml.full_load(file)
        with open(f"GenshinData/TW_simple_textMap.yaml", "r") as file:
            self.tw = yaml.full_load(file)
        with open(f"GenshinData/EN_full_textMap.json", "r") as file:
            self.full_en = json.load(file)
        with open(f"GenshinData/TW_full_textMap.json", "r") as file:
            self.full_tw = json.load(file)

    def getName(self, id: int, eng: bool = False) -> str:
        textMap = self.en if eng else self.tw
        return textMap.get(id) or id

    def getNameTextHash(self, text_hash: int, eng: bool = False) -> str:
        textMap = self.full_en if eng else self.full_tw
        return textMap.get(text_hash) or text_hash

get_name = GetName()


def defaultEmbed(title: str, message: str = ''):
    return discord.Embed(title=title, description=message, color=0xa68bd3)


def ayaakaaEmbed(title: str, message: str = ''):
    return discord.Embed(title=title, description=message, color=0xADC6E5)


def errEmbed(title: str, message: str = ''):
    return discord.Embed(title=title, description=message, color=0xfc5165)


def log(is_system: bool, is_error: bool, log_type: str, log_msg: str):
    now = datetime.now()
    today = datetime.today()
    current_date = today.strftime('%Y-%m-%d')
    current_time = now.strftime("%H:%M:%S")
    system = "SYSTEM"
    if not is_system:
        system = "USER"
    if not is_error:
        log_str = f"<{current_date} {current_time}> [{system}] ({log_type}) {log_msg}"
    else:
        log_str = f"<{current_date} {current_time}> [{system}] [ERROR] ({log_type}) {log_msg}"
    with open('log.txt', 'a+', encoding='utf-8') as f:
        f.write(f'{log_str}\n')
    return log_str


def getCharacterIcon(id: int):
    with open("GenshinData/chara_icon.yaml", "r") as file:
        chara_icon = yaml.full_load(file)
    return chara_icon.get(id)


def getStatEmoji(propid: str):
    emoji = stat_emojis.get(propid)
    return emoji if emoji != None else propid


def getClient():
    cookies = {"ltuid": 7368957,
               "ltoken": 'X5VJAbNxdKpMp96s7VGpyIBhSnEJr556d5fFMcT5'}
    client = genshin.Client(cookies)
    client.lang = "zh-tw"
    client.default_game = genshin.Game.GENSHIN
    client.uids[genshin.Game.GENSHIN] = 901211014
    return client


def trimCookie(cookie: str) -> str:
    try:
        new_cookie = ' '.join([
            re.search('ltoken=[0-9A-Za-z]{20,}', cookie).group(),
            re.search('ltuid=[0-9]{3,}', cookie).group(),
            re.search('cookie_token=[0-9A-Za-z]{20,}', cookie).group(),
            re.search('account_id=[0-9]{3,}', cookie).group()
        ])
    except:
        new_cookie = None
    return new_cookie


weekday_dict = {0: '週一', 1: '週二', 2: '週三', 3: '週四', 4: '週五', 5: '週六', 6: '週日'}


def getWeekdayName(n: int) -> str:
    return weekday_dict.get(n)
