import calendar
from datetime import timedelta
from typing import Dict, List, Optional

import discord
import enkanetwork
import genshin
import sentry_sdk
from dateutil.relativedelta import relativedelta
from discord.utils import format_dt

from ambr.client import AmbrTopAPI
from apps.draw import main_funcs
from apps.genshin.custom_model import (AbyssResult, AreaResult,
                                       CharacterResult, DiaryLogsResult,
                                       DiaryResult, DrawInput,
                                       GenshinAppResult, RealtimeNoteResult,
                                       ShenheAccount, ShenheBot, StatsResult)
from apps.genshin.utils import (get_character_emoji, get_shenhe_account,
                                get_uid, get_uid_tz)
from apps.text_map.text_map_app import text_map
from apps.text_map.utils import (get_element_name, get_month_name,
                                 get_user_locale)
from data.game.elements import element_emojis
from exceptions import UIDNotFound
from UI_base_models import get_error_handle_embed
from utility.utils import (DefaultEmbed, ErrorEmbed, get_dt_now,
                           get_user_appearance_mode, log)


def genshin_error_handler(func):
    async def inner_function(*args, **kwargs):
        genshin_app: GenshinApp = args[0]
        user_id = args[1]
        author_id = args[2]
        locale = args[-1]
        user = genshin_app.bot.get_user(user_id) or await genshin_app.bot.fetch_user(
            user_id
        )
        uid = await get_uid(user_id, genshin_app.bot.pool)
        author_locale = await get_user_locale(author_id, genshin_app.bot.pool)
        locale = author_locale or locale
        try:
            return await func(*args, **kwargs)
        except genshin.errors.DataNotPublic:
            embed = ErrorEmbed(description=f"{text_map.get(21, locale)}\nUID: {uid}")
            embed.set_author(
                name=text_map.get(22, locale),
                icon_url=user.display_avatar.url,
            )
            return GenshinAppResult(result=embed, success=False)
        except genshin.errors.InvalidCookies:
            embed = ErrorEmbed(description=f"{text_map.get(35, locale)}\nUID: {uid}")
            embed.set_author(
                name=text_map.get(36, locale),
                icon_url=user.display_avatar.url,
            )
            return GenshinAppResult(result=embed, success=False)
        except genshin.errors.GenshinException as e:
            log.warning(
                f"[Genshin App][GenshinException] in {func.__name__}: [e]{e} [code]{e.retcode} [msg]{e.msg}"
            )
            if e.retcode == -400005:
                embed = ErrorEmbed().set_author(name=text_map.get(14, locale))
                return GenshinAppResult(result=embed, success=False)
            else:
                sentry_sdk.capture_exception(e)
                embed = ErrorEmbed(description=f"```{e}```")
                embed.set_author(
                    name=text_map.get(10, locale),
                    icon_url=user.display_avatar.url,
                )
                return GenshinAppResult(result=embed, success=False)
        except Exception as e:
            log.warning(f"[Genshin App] Error in {func.__name__}: {e}")
            embed = get_error_handle_embed(user, e, locale)
            return GenshinAppResult(result=embed, success=False)

    return inner_function


class GenshinApp:
    def __init__(self, bot) -> None:
        self.bot: ShenheBot = bot

    @genshin_error_handler
    async def claim_daily_reward(
        self, user_id: int, author_id: int, locale: discord.Locale
    ):
        shenhe_user = await self.get_user_cookie(user_id, author_id, locale)
        try:
            reward = await shenhe_user.client.claim_daily_reward()
        except genshin.errors.AlreadyClaimed:
            return (
                ErrorEmbed().set_author(
                    name=text_map.get(40, locale, shenhe_user.user_locale),
                    icon_url=shenhe_user.discord_user.display_avatar.url,
                ),
                False,
            )
        else:
            return (
                DefaultEmbed(
                    description=f"{text_map.get(41, locale, shenhe_user.user_locale)} {reward.amount}x {reward.name}"
                ).set_author(
                    name=text_map.get(42, locale, shenhe_user.user_locale),
                    icon_url=shenhe_user.discord_user.display_avatar.url,
                ),
                True,
            )

    @genshin_error_handler
    async def get_real_time_notes(
        self, user_id: int, author_id: int, locale: discord.Locale
    ) -> GenshinAppResult:
        shenhe_user = await self.get_user_cookie(user_id, author_id, locale)
        notes = await shenhe_user.client.get_genshin_notes(shenhe_user.uid)
        draw_input = DrawInput(
            loop=self.bot.loop,
            session=self.bot.session,
            locale=shenhe_user.user_locale or str(locale),
            dark_mode=await get_user_appearance_mode(author_id, self.bot.pool),
        )
        embed = await self.parse_resin_embed(notes, locale, shenhe_user.user_locale)
        return GenshinAppResult(
            success=True,
            result=RealtimeNoteResult(embed=embed, draw_input=draw_input, notes=notes),
        )

    async def parse_resin_embed(
        self,
        notes: genshin.models.Notes,
        locale: discord.Locale,
        user_locale: Optional[str] = None,
    ) -> discord.Embed:
        if notes.current_resin == notes.max_resin:
            resin_recover_time = text_map.get(1, locale, user_locale)
        else:
            resin_recover_time = format_dt(notes.resin_recovery_time, "R")

        if notes.current_realm_currency == notes.max_realm_currency:
            realm_recover_time = text_map.get(1, locale, user_locale)
        else:
            realm_recover_time = format_dt(notes.realm_currency_recovery_time, "R")
        if (
            notes.remaining_transformer_recovery_time is None
            or notes.transformer_recovery_time is None
        ):
            transformer_recover_time = text_map.get(11, locale, user_locale)
        else:
            if notes.remaining_transformer_recovery_time.total_seconds() <= 0:
                transformer_recover_time = text_map.get(9, locale, user_locale)
            else:
                transformer_recover_time = format_dt(
                    notes.transformer_recovery_time, "R"
                )
        result = DefaultEmbed(
            description=f"""
                <:resin:1004648472995168326> {text_map.get(15, locale, user_locale)}: {resin_recover_time}
                <:realm:1004648474266062880> {text_map.get(15, locale, user_locale)}: {realm_recover_time}
                <:transformer:1004648470981902427> {text_map.get(8, locale, user_locale)}: {transformer_recover_time}
            """
        )
        if notes.expeditions:
            expedition_str = ""
            for expedition in notes.expeditions:
                if expedition.remaining_time.total_seconds() > 0:
                    expedition_str += f'{get_character_emoji(str(expedition.character.id))} {expedition.character.name} | {format_dt(expedition.completion_time, "R")}\n'
            if expedition_str:
                result.add_field(
                    name=text_map.get(20, locale, user_locale),
                    value=expedition_str,
                    inline=False,
                )
        result.set_image(url="attachment://realtime_notes.jpeg")
        return result

    @genshin_error_handler
    async def get_stats(
        self,
        user_id: int,
        author_id: int,
        namecard: enkanetwork.Namecard,
        avatar_asset: discord.Asset,
        locale: discord.Locale,
    ) -> GenshinAppResult:
        shenhe_user = await self.get_user_cookie(user_id, author_id, locale)
        uid = shenhe_user.uid
        if uid is None:
            raise UIDNotFound
        embed = DefaultEmbed()
        embed.set_image(url="attachment://stat_card.jpeg")
        fp = self.bot.stats_card_cache.get(uid)
        if fp is None:
            genshin_user = await shenhe_user.client.get_partial_genshin_user(uid)
            ambr = AmbrTopAPI(self.bot.session)
            characters = await ambr.get_character(
                include_beta=False, include_traveler=False
            )
            if not isinstance(characters, List):
                raise TypeError("Characters is not a list")

            mode = await get_user_appearance_mode(author_id, self.bot.pool)
            fp = await main_funcs.draw_stats_card(
                DrawInput(loop=self.bot.loop, session=self.bot.session, dark_mode=mode),
                namecard,
                genshin_user.stats,
                avatar_asset,
                len(characters),
            )
            self.bot.stats_card_cache[uid] = fp
        return GenshinAppResult(success=True, result=StatsResult(embed=embed, file=fp))

    @genshin_error_handler
    async def get_area(
        self, user_id: int, author_id: int, locale: discord.Locale
    ) -> GenshinAppResult:
        shenhe_user = await self.get_user_cookie(user_id, author_id, locale)
        uid = shenhe_user.uid
        if uid is None:
            raise UIDNotFound
        embed = DefaultEmbed()
        embed.set_author(
            name=text_map.get(58, locale, shenhe_user.user_locale),
            icon_url=shenhe_user.discord_user.display_avatar.url,
        )
        embed.set_image(url="attachment://area.jpeg")
        genshin_user = await shenhe_user.client.get_partial_genshin_user(uid)
        explorations = genshin_user.explorations
        fp = self.bot.area_card_cache.get(uid)
        if fp is None:
            mode = await get_user_appearance_mode(author_id, self.bot.pool)
            fp = await main_funcs.draw_area_card(
                DrawInput(loop=self.bot.loop, session=self.bot.session, dark_mode=mode),
                list(explorations),
            )
        result = {
            "embed": embed,
            "file": fp,
        }
        return GenshinAppResult(success=True, result=AreaResult(**result))

    @genshin_error_handler
    async def get_diary(
        self,
        user_id: int,
        author_id: int,
        locale: discord.Locale,
        month: Optional[int] = None,
    ) -> GenshinAppResult:
        shenhe_user = await self.get_user_cookie(user_id, author_id, locale)
        if shenhe_user.china:
            shenhe_user.client.region = genshin.Region.CHINESE
        user_timezone = get_uid_tz(shenhe_user.uid)
        now = get_dt_now() + timedelta(hours=user_timezone)
        if month is not None:
            now = now + relativedelta(months=month)
        diary = await shenhe_user.client.get_diary(month=now.month)
        if shenhe_user.uid is None:
            raise UIDNotFound
        user = await shenhe_user.client.get_partial_genshin_user(shenhe_user.uid)
        result = {}
        embed = DefaultEmbed()
        fp = await main_funcs.draw_diary_card(
            DrawInput(
                loop=self.bot.loop,
                session=self.bot.session,
                locale=shenhe_user.user_locale or locale,
                dark_mode=await get_user_appearance_mode(author_id, self.bot.pool),
            ),
            diary,
            user,
            now.month,
        )
        embed.set_image(url="attachment://diary.jpeg")
        embed.set_author(
            name=f"{text_map.get(69, locale, shenhe_user.user_locale)} • {get_month_name(now.month, locale, shenhe_user.user_locale)}",
            icon_url=shenhe_user.discord_user.display_avatar.url,
        )
        result["embed"] = embed
        result["file"] = fp
        return GenshinAppResult(success=True, result=DiaryResult(**result))

    @genshin_error_handler
    async def get_diary_logs(
        self, user_id: int, author_id: int, primo: bool, locale: discord.Locale
    ):
        shenhe_user = await self.get_user_cookie(user_id, author_id, locale)
        if shenhe_user.china:
            shenhe_user.client.region = genshin.Region.CHINESE

        now = get_dt_now()
        primo_per_day: Dict[int, int] = {}

        async for action in shenhe_user.client.diary_log(
            uid=shenhe_user.uid,
            month=now.month,
            type=genshin.models.DiaryType.PRIMOGEMS
            if primo
            else genshin.models.DiaryType.MORA,
        ):
            if action.time.day not in primo_per_day:
                primo_per_day[action.time.day] = 0
            primo_per_day[action.time.day] += action.amount

        before_adding: Dict[int, int] = primo_per_day.copy()
        before_adding = dict(sorted(before_adding.items()))

        for i in range(1, calendar.monthrange(now.year, now.month)[1] + 1):
            if i not in primo_per_day:
                primo_per_day[i] = 0

        primo_per_day = dict(sorted(primo_per_day.items()))

        return GenshinAppResult(
            success=True,
            result=DiaryLogsResult(
                primo_per_day=primo_per_day,
                before_adding=before_adding,
            ),
        )

    @genshin_error_handler
    async def get_abyss(
        self, user_id: int, author_id: int, previous: bool, locale: discord.Locale
    ) -> GenshinAppResult:
        shenhe_user = await self.get_user_cookie(user_id, author_id, locale)
        if shenhe_user.uid is None:
            raise UIDNotFound
        user = await shenhe_user.client.get_partial_genshin_user(shenhe_user.uid)
        abyss = await shenhe_user.client.get_genshin_spiral_abyss(
            shenhe_user.uid, previous=previous
        )
        characters = await shenhe_user.client.get_genshin_characters(shenhe_user.uid)
        author_locale = await get_user_locale(author_id, self.bot.pool)
        new_locale = author_locale or shenhe_user.user_locale or locale
        if not abyss.ranks.most_kills:
            embed = ErrorEmbed(description=text_map.get(74, new_locale))
            embed.set_author(
                name=text_map.get(76, new_locale),
                icon_url=shenhe_user.discord_user.display_avatar.url,
            )
            return GenshinAppResult(result=embed, success=False)
        result = {}
        result["abyss"] = abyss
        result["user"] = user
        result["discord_user"] = shenhe_user.discord_user
        result["characters"] = list(characters)
        overview = DefaultEmbed()
        overview.set_image(url="attachment://overview_card.jpeg")
        overview.set_author(
            name=f"{text_map.get(85, new_locale)} | {text_map.get(77, new_locale)} {abyss.season}",
            icon_url=shenhe_user.discord_user.display_avatar.url,
        )
        overview.set_footer(text=text_map.get(254, new_locale))
        dark_mode = await get_user_appearance_mode(author_id, self.bot.pool)
        cache = self.bot.abyss_overview_card_cache
        fp = cache.get(shenhe_user.uid)
        if fp is None:
            fp = await main_funcs.draw_abyss_overview_card(
                DrawInput(
                    loop=self.bot.loop,
                    session=self.bot.session,
                    locale=new_locale,
                    dark_mode=dark_mode,
                ),
                abyss,
                user,
            )
            cache[shenhe_user.uid] = fp
        result[
            "title"
        ] = f"{text_map.get(47, new_locale)} | {text_map.get(77, new_locale)} {abyss.season}"
        result["overview"] = overview
        result["overview_card"] = fp
        result["floors"] = [floor for floor in abyss.floors if floor.floor >= 9]
        result["uid"] = shenhe_user.uid
        return GenshinAppResult(result=AbyssResult(**result), success=True)

    @genshin_error_handler
    async def get_all_characters(
        self, user_id: int, author_id: int, locale: discord.Locale
    ) -> GenshinAppResult:
        shenhe_user = await self.get_user_cookie(user_id, author_id, locale)
        if shenhe_user.uid is None:
            raise UIDNotFound

        characters = await shenhe_user.client.get_genshin_characters(shenhe_user.uid)
        ambr = AmbrTopAPI(self.bot.session)
        all_characters = await ambr.get_character(include_beta=False)
        if not isinstance(all_characters, List):
            raise TypeError("all_characters is not a list")

        author_locale = await get_user_locale(author_id, self.bot.pool)
        new_locale = author_locale or shenhe_user.user_locale or str(locale)

        embed = DefaultEmbed(
            description=f"{text_map.get(576, new_locale).format(current=len(characters), total=len(all_characters)-1)}\n"
            f"{text_map.get(577, new_locale).format(current=len([c for c in characters if c.friendship == 10]), total=len(all_characters)-1)}"
        )
        embed.set_author(
            name=text_map.get(196, new_locale),
            icon_url=shenhe_user.discord_user.display_avatar.url,
        )
        embed.set_image(url="attachment://characters.jpeg")

        result = {
            "embeds": {"All": embed},
            "options": [
                discord.SelectOption(
                    label=f"{text_map.get(701, new_locale)} ({len(characters)})",
                    value="All",
                )
            ],
        }

        elements = {}
        for character in characters:
            if character.element not in elements:
                elements[character.element] = []
            elements[character.element].append(character)

        for element, chars in elements.items():
            total = len(
                [
                    c
                    for c in all_characters
                    if "10000007" not in c.id and c.element == element
                ]
            )
            embed = DefaultEmbed(
                description=f"{text_map.get(576, new_locale).format(current=len(chars), total=total)}\n"
                f"{text_map.get(577, new_locale).format(current=len([c for c in chars if c.friendship == 10]), total=total)}"
            )
            embed.set_author(
                name=text_map.get(196, new_locale),
                icon_url=shenhe_user.discord_user.display_avatar.url,
            )
            embed.set_image(url="attachment://characters.jpeg")
            result["embeds"][element] = embed

            result["options"].append(
                discord.SelectOption(
                    emoji=element_emojis.get(element),
                    label=f"{text_map.get(52, new_locale).format(element=get_element_name(element, new_locale))} ({len(chars)})",
                    value=element,
                )
            )

        fp = await main_funcs.character_summary_card(
            DrawInput(
                loop=self.bot.loop,
                session=self.bot.session,
                locale=new_locale,
                dark_mode=await get_user_appearance_mode(author_id, self.bot.pool),
            ),
            list(characters),
            "All",
        )
        result["file"] = fp
        result["characters"] = list(characters)

        return GenshinAppResult(result=CharacterResult(**result), success=True)

    @genshin_error_handler
    async def redeem_code(
        self, user_id: int, author_id: int, code: str, locale: discord.Locale
    ) -> GenshinAppResult:
        shenhe_user = await self.get_user_cookie(user_id, author_id, locale)
        try:
            await shenhe_user.client.redeem_code(code)
        except genshin.errors.RedemptionClaimed:
            return GenshinAppResult(
                result=ErrorEmbed(
                    description=f"{text_map.get(108, locale, shenhe_user.user_locale)}: {code}"
                ).set_author(
                    name=text_map.get(106, locale, shenhe_user.user_locale),
                    icon_url=shenhe_user.discord_user.display_avatar.url,
                ),
                success=False,
            )
        except genshin.errors.RedemptionInvalid:
            return GenshinAppResult(
                result=ErrorEmbed(
                    description=f"{text_map.get(108, locale, shenhe_user.user_locale)}: {code}"
                ).set_author(
                    name=text_map.get(107, locale, shenhe_user.user_locale),
                    icon_url=shenhe_user.discord_user.display_avatar.url,
                ),
                success=False,
            )
        except genshin.errors.RedemptionCooldown:
            return GenshinAppResult(
                result=ErrorEmbed(
                    description=f"{text_map.get(108, locale, shenhe_user.user_locale)}: {code}"
                ).set_author(
                    name=text_map.get(133, locale, shenhe_user.user_locale),
                    icon_url=shenhe_user.discord_user.display_avatar.url,
                ),
                success=False,
            )
        else:
            return GenshinAppResult(
                result=DefaultEmbed(
                    description=f"{text_map.get(108, locale, shenhe_user.user_locale)}: {code}"
                ).set_author(
                    name=text_map.get(109, locale, shenhe_user.user_locale),
                    icon_url=shenhe_user.discord_user.display_avatar.url,
                ),
                success=True,
            )

    @genshin_error_handler
    async def get_activities(
        self, user_id: int, author_id: int, locale: discord.Locale
    ) -> GenshinAppResult:
        shenhe_user = await self.get_user_cookie(user_id, author_id, locale)
        uid = shenhe_user.uid
        if uid is None:
            raise UIDNotFound
        activities = await shenhe_user.client.get_genshin_activities(uid)
        summer = activities.summertime_odyssey
        if summer is None:
            return GenshinAppResult(
                success=False,
                result=ErrorEmbed().set_author(
                    name=text_map.get(110, locale, shenhe_user.user_locale),
                    icon_url=shenhe_user.discord_user.display_avatar.url,
                ),
            )
        result = await self.parse_summer_embed(
            summer,
            shenhe_user.discord_user,
            shenhe_user.user_locale or str(locale),
        )
        return GenshinAppResult(result=result, success=True)

    async def parse_summer_embed(
        self,
        summer: genshin.models.Summer,
        user: discord.User | discord.Member | discord.ClientUser,
        locale: discord.Locale | str,
    ) -> list[discord.Embed]:
        embeds = []
        embed = DefaultEmbed().set_author(
            name=text_map.get(111, locale),
            icon_url=user.display_avatar.url,
        )
        embed.add_field(
            name=f"<:SCORE:983948729293897779> {text_map.get(43, locale)}",
            value=f"{text_map.get(112, locale)}: {summer.waverider_waypoints}/13\n"
            f"{text_map.get(113, locale)}: {summer.waypoints}/10\n"
            f"{text_map.get(114, locale)}: {summer.treasure_chests}",
        )
        embed.set_image(url="https://i.imgur.com/Zk1tqxA.png")
        embeds.append(embed)
        embed = DefaultEmbed().set_author(
            name=text_map.get(111, locale),
            icon_url=user.display_avatar.url,
        )
        surfs = summer.surfpiercer
        value = ""
        for surf in surfs:
            if surf.finished:
                minutes, seconds = divmod(surf.time, 60)
                time_str = (
                    f"{minutes} {text_map.get(7, locale)} {seconds} sec."
                    if minutes != 0
                    else f"{seconds}{text_map.get(12, locale)}"
                )
                value += f"{surf.id}. {time_str}\n"
            else:
                value += f"{surf.id}. *{text_map.get(115, locale)}* \n"
        embed.add_field(name=text_map.get(116, locale), value=value)
        embed.set_thumbnail(url="https://i.imgur.com/Qt4Tez0.png")
        embeds.append(embed)
        memories = summer.memories
        for memory in memories:
            embed = DefaultEmbed().set_author(
                name=text_map.get(117, locale),
                icon_url=user.display_avatar.url,
            )
            embed.set_thumbnail(url="https://i.imgur.com/yAbpUF8.png")
            embed.set_image(url=memory.icon)
            embed.add_field(
                name=memory.name,
                value=f"{text_map.get(119, locale)}: {memory.finish_time}",
            )
            embeds.append(embed)
        realms = summer.realm_exploration
        for realm in realms:
            embed = DefaultEmbed().set_author(
                name=text_map.get(118, locale),
                icon_url=user.display_avatar.url,
            )
            embed.set_thumbnail(url="https://i.imgur.com/0jyBciz.png")
            embed.set_image(url=realm.icon)
            embed.add_field(
                name=realm.name,
                value=f"{text_map.get(119, locale)}: {realm.finish_time if realm.finished else text_map.get(115, locale)}\n"
                f"{text_map.get(120, locale)} {realm.success} {text_map.get(121, locale)}\n"
                f"{text_map.get(122, locale)} {realm.skills_used} {text_map.get(121, locale)}",
            )
            embeds.append(embed)
        return embeds

    async def get_user_uid(self, user_id: int) -> int | None:
        uid = await get_uid(user_id, self.bot.pool)
        return uid

    async def get_user_cookie(
        self, user_id: int, author_id: int, locale: Optional[discord.Locale] = None
    ) -> ShenheAccount:
        author_locale = await get_user_locale(author_id, self.bot.pool)
        shenhe_user = await get_shenhe_account(
            user_id, self.bot, locale, author_locale=author_locale
        )
        return shenhe_user
