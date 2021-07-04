# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2021 nickofolas
import discord


class MenuActions(discord.ui.View):
    def __init__(self, menu):
        super().__init__()
        self.menu = menu

    async def interaction_check(self, interaction):
        (predicates := []).append(interaction.user.id in (
            self.menu.author.id,
            *self.menu.bot.owner_ids,
            self.menu.bot.owner_id)
        )
        return all(predicates)

    @discord.ui.button(label="<")
    async def previous(self, button, interaction):
        current_page = self.menu.get_current_page(self.menu.current_page - 1)
        send_kwargs = self.menu._get_msg_kwargs(current_page)
        await interaction.response.edit_message(**send_kwargs)

    @discord.ui.button(label="⨉")
    async def close(self, button, interaction):
        self.stop()
        await self.menu.close(manual=True)

    @discord.ui.button(label=">")
    async def next(self, button, interaction):
        current_page = self.menu.get_current_page(self.menu.current_page + 1)
        send_kwargs = self.menu._get_msg_kwargs(current_page)
        await interaction.response.edit_message(**send_kwargs)
