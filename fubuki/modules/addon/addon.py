from discord.ext import commands

class Addon(commands.Cog):

    def add_command(self, command):
        '''
        Add a commands.Command or a subclass of it to a loaded Addon
        
        If a commands.Group is encountered, all subcommands will also be recursively added
        '''
        _original_command = command

        _current_commands = list(self.__cog_commands__)
        _current_commands.append(command)
        self.__cog_commands__ = tuple(_current_commands)

        for _old_command in self.walk_commands():
            self.bot.remove_command(_old_command.name) # No dupe cmd errors

        self._inject(self.bot) # Re-add everything

        if isinstance(_original_command, commands.Group):
            for subcmd in command.walk_commands():
                if isinstance(subcmd, commands.Group): # Recursively add sub-groups
                    self.add_command(subcmd)
                subcmd.cog = self # Update the subcmds

        return self.bot.get_command(command.name)
