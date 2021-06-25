from sys import version as py_version
from types import SimpleNamespace
from typing import Union

import discord
import neo
from discord.ext import commands
from neo.modules import Paginator, args, cse, dictionary
from neo.types.converters import mention_converter

DELTA_FORMAT = "{0.months} months and {0.days} days ago"
BADGE_MAPPING = {
    "staff": "<:staff:743223905812086865>",
    "partner": "<:partner:743223905820606588>",
    "hypesquad": "<:events:743223907271573595>",
    "hypesquad_balance": "<:balance:743223907301064704>",
    "hypesquad_bravery": "<:bravery:743223907519299694>",
    "hypesquad_brilliance": "<:brilliance:743223907372499046>",
    "bug_hunter": "<:bug1:743223907380756591>",
    "bug_hunter_level_2": "<:bug2:743223907129098311>",
    "verified_bot_developer": "<:dev:743223907246407761>",
    "early_supporter": "<:early:743223907338944522>"
}
ICON_MAPPING = {
    "owner": "<:serverowner:743224805855330304>",
    "bot": "<:bot:743223907238281217>",
    "verified_bot": "<:verified1:743228362339909665><:verified2:743228362251829339>"
}


def _result_to_embed(result):
    embed = neo.Embed(
        title=result.title,
        description=result.snippet,
        url=result.url
    )
    embed.set_image(url=result.image_url or "")
    return embed


def _definitions_to_embed(word):
    for meaning in word.meanings:
        for definition in meaning.definitions:
            embed = neo.Embed(
                description=definition.definition
            ).set_author(
                name=f"{word.word}: {meaning.part_of_speech}"
            ).add_field(
                name="Synonyms",
                value=", ".join((definition.synonyms or ["No synonyms"])[:5])
            )
            yield embed


class InfoButtons(discord.ui.View):
    def __init__(self, privacy_embed: neo.Embed):
        self.privacy_embed = privacy_embed
        super().__init__(timeout=60)

    @discord.ui.button(label="View Privacy information", row=1)
    async def callback(self, button, interaction: discord.Interaction):
        await interaction.response.defer()
        await interaction.followup.send(
            embed=self.privacy_embed, ephemeral=True
        )


class Utility(neo.Addon):
    """Various utility commands"""
    def __init__(self, bot: neo.Neo):
        self.bot = bot
        self.privacy_embed = neo.Embed(
            title="Privacy Information",
            description=bot.cfg["privacy_info"]
        )
        self.bot.loop.create_task(self.__ainit__())

    async def __ainit__(self):
        await self.bot.wait_until_ready()

        # These both take a ClientSession, so we wait until ready so we can use the bot's
        self.google = cse.Search(
            key=self.bot.cfg["bot"]["cse_keys"],
            engine_id=self.bot.cfg["bot"]["cse_engine"],
            session=self.bot.session
        )
        self.dictionary = dictionary.Define(self.bot.session)
        self.appinfo = await self.bot.application_info()

    @args.add_arg(
        "query",
        nargs="+",
        help="The query which will searched for on Google",
    )
    @args.add_arg(
        "-i", "--image",
        action="store_true",
        help="Toggles whether or not Google Images will be searched"
    )
    @args.command(name="google", aliases=["g"])
    async def google_command(self, ctx, *, query):
        """Search Google for a query"""
        resp = await self.google.search(
            " ".join(query.query),
            image=query.image)

        embeds = [*map(_result_to_embed, resp)]
        if not embeds:
            raise RuntimeError("Search returned no results")

        menu = Paginator.from_embeds(embeds)
        await menu.start(ctx)

    @commands.command(name="image", aliases=["i"])
    async def google_image_shortcut(self, ctx, *, query):
        """A shortcut for `google --image <query>`"""
        await self.google_command(
            ctx, query=SimpleNamespace(
                query=query, image=True
            ))

    @args.add_arg(
        "word",
        nargs="+",
        help="The word to search a dictionary for"
    )
    @args.add_arg(
        "-lc", "--lang_code",
        default="en",
        help="The language code of the dictionary to search"
    )
    @args.command(name="define")
    async def dictionary_command(self, ctx, *, query):
        """Search the dictionary for a word's definition"""
        resp = await self.dictionary.define(
            " ".join(query.word),
            lang_code=query.lang_code
        )

        embeds = []
        for word in resp.words:
            embeds.extend(_definitions_to_embed(word))
        if not embeds:
            raise RuntimeError("No definition found")

        menu = Paginator.from_embeds(embeds)
        await menu.start(ctx)

    @commands.command(name="avatar", aliases=["av", "avy", "pfp"])
    async def avatar_command(self, ctx, *, user: Union[int, mention_converter] = None):
        """Retrieves the avatar of yourself, or a specified user"""
        user = await self.bot.fetch_user(user) if user else ctx.author
        url = user.avatar

        embed = neo.Embed(
            description=f"[View in browser]({url})"
        ).set_image(url=url).set_footer(text=str(user))

        await ctx.send(embed=embed)

    @commands.command(name="userinfo", aliases=["ui"])
    async def user_info_command(self, ctx, *, user: Union[mention_converter, int, discord.Member] = None):
        """Retrieves information of yourself, or a specified user"""
        if isinstance(user, (int, type(None))):
            try:
                user = await ctx.guild.fetch_member(user or ctx.author.id)
            except (discord.HTTPException, AttributeError):
                user = await self.bot.fetch_user(user or ctx.author.id)

        embed = neo.Embed().set_thumbnail(url=user.avatar)
        flags = [BADGE_MAPPING[f.name] for f in user.public_flags.all() if BADGE_MAPPING.get(f.name)]
        title = str(user)
        description = " ".join(flags) + ("\n" if flags else "")
        description += f"**Created** <t:{int(user.created_at.timestamp())}:D>"

        if user.bot:
            title = "{0} {1}".format(
                ICON_MAPPING["verified_bot"] if user.public_flags.verified_bot else ICON_MAPPING["bot"],
                title)

        if isinstance(user, discord.Member):
            description += f"\n**Joined** <t:{int(user.joined_at.timestamp())}:D>"
            if user.id == ctx.guild.owner_id:
                title = "{0} {1}".format(ICON_MAPPING["owner"], title)

        embed.title = title
        embed.description = description

        await ctx.send(embed=embed)

    @commands.command(name="info", aliases=["about"])
    async def neo_info_command(self, ctx):
        """Show information about neo phoenix"""
        embed = neo.Embed(
            description=(
                "**neo Version** {0}"
                "\n**Server Count** {1}"
                "\n**Startup Time** <t:{2}>"
                "\n\n**Python Version** {3}"
                "\n**Discord.py Version** {4}"
            ).format(
                neo.__version__,
                len(self.bot.guilds),
                self.bot.boot_time,
                py_version.split(" ", 1)[0],
                discord.__version__
            )
        )
        embed.set_thumbnail(url=self.bot.user.avatar)
        embed.set_author(
            name=f"Developed by {self.appinfo.owner}",
            icon_url=self.appinfo.owner.avatar
        )

        buttons = InfoButtons(self.privacy_embed)
        buttons.add_item(discord.ui.Button(
            url=self.bot.cfg["invite_url"],
            label="Invite neo phoenix",
            style=discord.ButtonStyle.secondary,
            disabled=not self.appinfo.bot_public
        ))
        buttons.add_item(discord.ui.Button(
            url=self.bot.cfg["upstream_url"],
            label="Source Code",
            style=discord.ButtonStyle.secondary
        ))
        await ctx.send(embed=embed, view=buttons)


def setup(bot):
    bot.add_cog(Utility(bot))
