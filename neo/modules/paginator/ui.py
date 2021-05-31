import discord


class MenuButton(discord.ui.Button):
    def __init__(self, menu):
        super().__init__(style=self.style, label=self.label)
        self.menu = menu


class Previous(MenuButton):
    style = discord.ButtonStyle.primary
    label = "<"

    async def callback(self, interaction):
        current_page = self.menu.get_current_page(self.menu.current_page - 1)
        send_kwargs = self.menu._get_msg_kwargs(current_page)

        await interaction.response.edit_message(**send_kwargs)


class Close(MenuButton):
    style = discord.ButtonStyle.danger
    label = "X"

    async def callback(self, interaction):
        self.view.stop()
        await self.menu.close(manual=True)


class Next(MenuButton):
    style = discord.ButtonStyle.primary
    label = ">"

    async def callback(self, interaction):
        current_page = self.menu.get_current_page(self.menu.current_page + 1)
        send_kwargs = self.menu._get_msg_kwargs(current_page)

        await interaction.response.edit_message(**send_kwargs)


class MenuActions(discord.ui.View):
    def __init__(self, menu, timeout):
        super().__init__(timeout=timeout)
        self.menu = menu

        for button in (Previous, Close, Next):
            self.add_item(button(self.menu))

    async def on_timeout(self):
        self.stop()

    async def interaction_check(self, interaction):
        predicates = []
        predicates.append(interaction.user.id in (
            self.menu.author.id,
            *self.menu.bot.owner_ids,
            self.menu.bot.owner_id)
        )
        predicates.append(interaction.message.id == self.menu.message.id)
        return all(predicates)
