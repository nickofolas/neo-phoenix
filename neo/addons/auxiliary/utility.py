# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2021 nickofolas
"""
An auxiliary module for the `Utility` addon
"""
import discord
import neo


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
            f"**Invite neo phoenix with this URL:**\n{url}",
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
    def __init__(self, *args, **kwargs):
        kwargs["style"] = discord.ButtonStyle.primary
        kwargs["label"] = "Invite neo phoenix"
        kwargs["custom_id"] = "neo phoenix:invite button"
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
            view=self.view.invite_menu
        )


class InfoButtons(discord.ui.View):
    def __init__(
        self,
        privacy_embed: neo.Embed,
        invite_disabled: bool,
        invite_menu: InviteMenu
    ):
        self.privacy_embed = privacy_embed
        self.invite_menu = invite_menu
        super().__init__(timeout=None)
        self.add_item(InviteButton(disabled=invite_disabled))

    @discord.ui.button(
        custom_id="neo phoenix:privacy policy",
        label="Privacy Policy",
        row=1
    )
    async def callback(self, button, interaction: discord.Interaction):
        await interaction.response.send_message(
            embed=self.privacy_embed, ephemeral=True
        )
