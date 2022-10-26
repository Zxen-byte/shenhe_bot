from typing import Any

import aiosqlite
from discord import Embed, File, Interaction, Locale, SelectOption, User
from discord.ui import Select

import config
from apps.text_map.text_map_app import text_map
from apps.text_map.utils import get_user_locale
from UI_base_models import BaseView
from utility.utils import default_embed, get_user_appearance_mode
from yelan.draw import draw_abyss_floor_card, draw_abyss_one_page


class View(BaseView):
    def __init__(
        self,
        author: User,
        embeds: list[Embed],
        locale: Locale,
        user_locale: str,
        db: aiosqlite.Connection,
    ):
        super().__init__(timeout=config.mid_timeout)
        self.author = author
        self.db = db

        self.add_item(FloorSelect(embeds, locale, user_locale))


class FloorSelect(Select):
    def __init__(self, embeds: list[Embed], locale: Locale, user_locale: str):
        options = [
            SelectOption(label=text_map.get(43, locale, user_locale), value="overview")
        ]
        for index in range(0, len(embeds["floors"])):
            options.append(
                SelectOption(
                    label=f"{text_map.get(146, locale, user_locale)} {9+index} {text_map.get(147, locale, user_locale)}",
                    value=index,
                )
            )
        super().__init__(
            placeholder=text_map.get(148, locale, user_locale), options=options
        )
        self.add_option(label=text_map.get(643, locale, user_locale), value="one-page")
        self.embeds = embeds

    async def callback(self, i: Interaction) -> Any:
        await i.response.defer()
        dark_mode = await get_user_appearance_mode(i.user.id, i.client.db)
        user_locale = await get_user_locale(i.user.id, i.client.db)
        if self.values[0] == "overview":
            fp = self.embeds["overview_card"]
            fp.seek(0)
            image = File(fp, filename="overview_card.jpeg")
            await i.edit_original_response(
                embed=self.embeds["overview"],
                attachments=[image],
            )
        elif self.values[0] == "one-page":
            embed = default_embed()
            embed.set_author(
                name=text_map.get(644, i.locale, user_locale),
                icon_url="https://i.imgur.com/V76M9Wa.gif",
            )
            await i.edit_original_response(embed=embed, attachments=[])
            cache = i.client.abyss_one_page_cache
            key = self.embeds["user"].info.nickname
            fp = cache.get(key)
            if fp is None:
                fp = await draw_abyss_one_page(
                    self.embeds["user"],
                    self.embeds["abyss"],
                    user_locale or i.locale,
                    dark_mode,
                    i.client.session,
                )
                cache[key] = fp
            fp.seek(0)
            image = File(fp, filename="abyss_one_page.jpeg")
            embed = default_embed()
            embed.set_image(url="attachment://abyss_one_page.jpeg")
            embed.set_author(
                name=self.embeds["title"], icon_url=i.user.display_avatar.url
            )
            await i.edit_original_response(embed=embed, attachments=[image])
        else:
            embed = default_embed()
            embed.set_author(
                name=text_map.get(644, i.locale, user_locale),
                icon_url="https://i.imgur.com/V76M9Wa.gif",
            )
            await i.edit_original_response(embed=embed, attachments=[])
            embed = default_embed()
            embed.set_image(url="attachment://floor.jpeg")
            embed.set_author(
                name=self.embeds["title"], icon_url=i.user.display_avatar.url
            )
            cache = i.client.abyss_floor_card_cache
            key = str(self.embeds["floors"][int(self.values[0])])
            fp = cache.get(key)
            if fp is None:
                fp = await draw_abyss_floor_card(
                    dark_mode,
                    self.embeds["floors"][int(self.values[0])],
                    i.client.session,
                )
                cache[key] = fp
            fp.seek(0)
            image = File(fp, filename="floor.jpeg")
            await i.edit_original_response(embed=embed, attachments=[image])
