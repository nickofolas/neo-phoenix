# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2021 nickofolas
"""
An auxiliary module for the `Utility` addon
"""
import asyncio
import re
from functools import cache

import discord
import neo

_language_codes = neo.formatters.Table()
_language_codes.init_columns("Lang Code", "Lang")
for code, lang in [
    ("en_US", "US English"),
    ("hi", "Hindi"),
    ("es", "Spanish"),
    ("fr", "French"),
    ("ja", "Japanese"),
    ("ru", "Russian"),
    ("en_GB", "UK English"),
    ("de", "German"),
    ("it", "Italian"),
    ("ko", "Korean"),
    ("pt-BR", "Portuguese"),
    ("ar", "Arabic"),
    ("tr", "Turkish")
]:
    _language_codes.add_row(code, lang)
LANGUAGE_CODES = _language_codes.display()
TRANSLATION_DIRECTIVE = re.compile(
    r"((?P<src>[a-zA-Z\*\_]+|auto)->(?P<dest>[a-zA-Z]+))?"
)


def result_to_embed(result):
    embed = neo.Embed(
        title=result.title,
        description=result.snippet,
        url=result.url
    )
    embed.set_image(url=result.image_url or "")
    return embed


def definitions_to_embed(word):
    for meaning in word.meanings[:25]:  # Slice at 25 to fit within dropdown limits
        for definition in meaning.definitions:
            embed = neo.Embed(
                description=definition.definition,
                title=f"{word.word}: {meaning.part_of_speech}"
            ).add_field(
                name="Synonyms",
                value=", ".join((definition.synonyms or ["No synonyms"])[:5])
            )
            yield embed


def get_translation_kwargs(content: str) -> tuple[str, dict[str, str]]:
    kwargs = {"dest": "en", "src": "auto"}
    if (match := TRANSLATION_DIRECTIVE.match(content))[0]:
        content = content.replace(match[0], "")
        kwargs = match.groupdict()
        if kwargs["src"] in {"*", "_"}:
            kwargs["src"] = "auto"

    return content.casefold().strip(), kwargs


@cache  # Prevent repeated requests when possible
def do_translate(translator, content: str, *, dest: str, src: str):
    try:
        translation = translator.translate(content, dest=dest, src=src)
    except ValueError as e:
        e.args = (f"An {e.args[0]} was provided",)
        raise
    except Exception:
        raise RuntimeError("Something went wrong with translation. Maybe try again later?")
    return translation


async def translate(translator, *args, **kwargs):  # Lazy async wrapper
    return await asyncio.to_thread(do_translate, translator, *args, **kwargs)


class InviteDropdown(discord.ui.Select):
    def __init__(self, *args, **kwargs):
        kwargs["custom_id"] = "neo phoenix:invite dropdown menu"
        super().__init__(*args, **kwargs)

    async def callback(self, interaction: discord.Interaction):
        url = discord.utils.oauth_url(
            self.view.application_id,
            permissions=discord.Permissions(int(self.values[0]))
        )
        await interaction.response.send_message(
            f"[**Click here to invite neo phoenix**]({url})",
            ephemeral=True
        )


class InviteMenu(discord.ui.View):
    def __init__(self, presets: list[dict[str, str]], application_id: int):
        self.application_id = application_id
        super().__init__(timeout=None)
        dropdown = InviteDropdown(placeholder="Choose Invite Preset")
        for preset in presets:
            dropdown.add_option(
                label=preset["name"],
                description=preset["desc"],
                value=preset["value"]
            )
        self.add_item(dropdown)


class InviteButton(discord.ui.Button):
    def __init__(self, *args, view_kwargs: dict, **kwargs):
        kwargs["style"] = discord.ButtonStyle.primary
        kwargs["label"] = "Invite neo phoenix"
        kwargs["custom_id"] = "neo phoenix:invite button"
        self.view_kwargs = view_kwargs
        super().__init__(*args, **kwargs)

    async def callback(self, interaction: discord.Interaction):
        embed = neo.Embed(
            title="Select a permissions preset below.",
            description="**Managed Role** A role assigned to neo phoenix by "
            "Discord automatically. This role cannot be deleted while the "
            "bot is in a server. Consider `No Permissions` to avoid managed roles."
            "\n\n**Everything** This can be used to be selective with permissions by "
            "disabling what you don't want to grant."
        )
        await interaction.response.send_message(
            embed=embed,
            ephemeral=True,
            view=InviteMenu(**self.view_kwargs)
        )


class InfoButtons(discord.ui.View):
    def __init__(
        self,
        privacy_embed: neo.Embed,
        invite_disabled: bool,
        *,
        buttons: list[discord.ui.Button],
        **invite_menu_kwargs
    ):
        self.privacy_embed = privacy_embed
        super().__init__(timeout=None)
        self.add_item(InviteButton(
            view_kwargs=invite_menu_kwargs, disabled=invite_disabled))
        for button in buttons:
            self.add_item(button)

    @discord.ui.button(
        custom_id="neo phoenix:privacy policy",
        label="Privacy Policy",
        row=1
    )
    async def callback(self, button, interaction: discord.Interaction):
        await interaction.response.send_message(
            embed=self.privacy_embed, ephemeral=True
        )
