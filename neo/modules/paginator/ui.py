import discord

class PagerButton(discord.ui.Button):
    def __init__(self, menu, action):
        super().__init__(style=discord.ButtonStyle.primary, label=action.title())
        self.action = action
        self.menu = menu

    async def callback(self, interaction):
        await interaction.response.edit_message(content="lmao")

class CloseButton(discord.ui.Button):
    def __init__(self, menu):
        super().__init__(style=discord.ButtonStyle.danger, label="Close")
        self.menu = menu

class MenuActions(discord.ui.View):
    def __init__(self, menu):
        super().__init__()
        self.menu = menu

        buttons = []
        for action in ("previous", "next"):
            buttons.append(PagerButton(self.menu, action))
        buttons.insert(1, CloseButton(self.menu))

        [*map(self.add_item, buttons)]
