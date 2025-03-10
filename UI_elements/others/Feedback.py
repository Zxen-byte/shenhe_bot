from UI_base_models import BaseModal
from discord import Locale, TextStyle, Interaction
from discord.ui import TextInput
from apps.text_map.text_map_app import text_map
import config
from utility.utils import DefaultEmbed


class FeedbackModal(BaseModal):
    feedback = TextInput(label="feedback", style=TextStyle.long)

    def __init__(self, locale: Locale | str):
        super().__init__(title=text_map.get(724, locale), timeout=config.long_timeout)
        self.feedback.label = text_map.get(724, locale)

        self.locale = locale

    async def on_submit(self, i: Interaction) -> None:
        await i.response.send_message(
            embed=DefaultEmbed().set_author(
                name=text_map.get(725, self.locale), icon_url=i.user.display_avatar.url
            ),
            ephemeral=True,
        )
        seria = i.client.get_user(410036441129943050) or await i.client.fetch_user(
            410036441129943050
        )
        await seria.send(
            embed=DefaultEmbed(description=self.feedback.value).set_author(
                name=str(i.user), icon_url=i.user.display_avatar.url
            ).set_footer(text=i.user.id)
        )
