from typing import List
from UI_base_models import BaseView
import config
from data.game.elements import get_element_emoji, get_element_list
from discord import SelectOption, SelectOption, Interaction, Locale
from discord import ui
import genshin
from utility.utils import divide_chunks
from apps.text_map.text_map_app import text_map
from discord import utils


class View(BaseView):
    def __init__(
        self, locale: Locale | str, characters: List[genshin.models.Character]
    ):
        super().__init__(timeout=config.mid_timeout)
        self.locale = locale
        self.characters = characters

        elements = get_element_list()
        for index, element in enumerate(elements):
            self.add_item(
                ElementButton(element, get_element_emoji(element), index // 4)
            )


class ElementButton(ui.Button):
    def __init__(self, emoji: str, element: str, row: int):
        super().__init__(emoji=emoji, row=row)
        self.element = element

    async def callback(self, i: Interaction):
        self.view: View
        self.view.clear_items()

        select_options: List[SelectOption] = []
        for character in self.view.characters:
            if character.element == self.element:
                select_options.append(
                    SelectOption(label=character.name, value=str(character.id))
                )
        
        split_options = list(divide_chunks(select_options, 25))
        for index, options in enumerate(split_options, start=1):
            self.view.add_item(
                CharacterSelect(f"{text_map.get(157, self.view.locale)} ({index})", options)
            )


class CharacterSelect(ui.Select):
    def __init__(self, placeholder: str, options: List[SelectOption]):
        super().__init__(placeholder=placeholder, options=options)

    async def callback(self, i: Interaction):
        self.view: View
        
        character_id = int(self.values[0])
        character = utils.get(self.view.characters, id=character_id)
        
