# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2021 nickofolas
from functools import partial
from sys import version as py_version
from types import SimpleNamespace
from typing import Union

import discord
import neo
from discord.ext import commands
from googletrans import LANGUAGES, Translator
from neo.modules import DropdownMenu, EmbedPages, args, cse, dictionary
from neo.tools import shorten
from neo.types.converters import mention_converter

from .auxiliary.utility import (
    LANGUAGE_CODES,
    InfoButtons,
    InviteMenu,
    definitions_to_embed,
    get_translation_kwargs,
    result_to_embed,
    translate
)

BADGE_MAPPING = {
    "staff": "<:_:863197443386900541>",
    "discord_certified_moderator": "<:_:863197442996305960>",
    "partner": "<:_:863197443311403008>",
    "hypesquad": "<:_:863197443281911808>",
    "hypesquad_balance": "<:_:863197443244294164>",
    "hypesquad_bravery": "<:_:863197443238920242>",
    "hypesquad_brilliance": "<:_:863197443268673567>",
    "bug_hunter": "<:_:863197442983067678>",
    "bug_hunter_level_2": "<:_:863197443083730955>",
    "early_verified_bot_developer": "<:_:863197443083730958>",
    "early_supporter": "<:_:863197442840068117>",
}
ICON_MAPPING = {
    "guild_owner": "<:_:863197442996305941>",
    "bot_tag": "<:_:863197442937061416>",
    "verified_bot_tag": "<:_:863197443083730959><:_:863197443565813780>"
}
PREMIUM_ICON_MAPPING = {
    0: "",
    1: "<:_:868138562690875452>",
    2: "<:_:868138562737041458>",
    3: "<:_:868138562913173564>"
}


class Utility(neo.Addon):
    """Various utility commands"""

    def __init__(self, bot: neo.Neo):
        self.bot = bot
        with open(bot.cfg["privacy_policy_path"]) as policy:
            header, body = policy.read().split("\n", 1)
            header = header.lstrip("# ")
            body = body.replace("  \n", "\n")  # Ensure proper formatting on mobile
        self.privacy_embed = neo.Embed(title=header, description=body)
        self.translator = Translator(raise_exception=True)
        bot.loop.create_task(self.__ainit__())

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
        buttons = [
            discord.ui.Button(
                url=self.bot.cfg["support"]["url"],
                label="Support Server",
                disabled=self.bot.cfg["support"]["disabled"],
            ),
            discord.ui.Button(
                url=self.bot.cfg["upstream_url"],
                label="Source Code",
                row=1
            )
        ]
        self.info_buttons = partial(
            InfoButtons,
            self.privacy_embed,
            False,  # not self.appinfo.bot_public,
            buttons=buttons,
            presets=self.bot.cfg["invite_presets"],
            application_id=self.bot.user.id
        )
        self.bot.add_view(self.info_buttons())

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

        embeds = [*map(result_to_embed, resp)]
        if not embeds:
            raise RuntimeError("Search returned no results")

        pages = EmbedPages(embeds)
        menu = DropdownMenu.from_pages(
            pages, embed_auto_label=True, embed_auto_desc=True)
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
        default="en_US",
        help="The language code of the dictionary to search\n```\n"
        + LANGUAGE_CODES + "\n```Defaults to `en_US`"
    )
    @args.command(name="define")
    async def dictionary_command(self, ctx, *, query):
        """Search the dictionary for a word's definition"""
        try:
            resp = await self.dictionary.define(
                " ".join(query.word),
                lang_code=query.lang_code
            )
        except dictionary.DefinitionError:
            raise RuntimeError("No definition found")

        embeds = []
        for word in resp.words:
            embeds.extend(definitions_to_embed(word))
        if not embeds:
            raise RuntimeError("No definition found")

        pages = EmbedPages(embeds)
        menu = DropdownMenu.from_pages(
            pages, embed_auto_label=True, embed_auto_desc=True)
        await menu.start(ctx)

    @commands.command(
        name="translate",
        aliases=["tr"],
        usage="[directive] <content>"
    )
    async def translation_command(self, ctx, *, input):
        """
        Translate a string of text

        If just a string of text is supplied, the source language will be
        auto-detected and translated to English.
        Ex: `translate amigo`

        To translate between particular languages, use the `->` operator.
        Ex: `translate en->ja Hello` *Translates "hello" to Japanese*
        Ex: `translate *->ja Hello` *Same as above, but auto-detects source language*
        """
        content, kwargs = get_translation_kwargs(input)
        translated = await translate(self.translator, content, **kwargs)
        embed = neo.Embed(
            description=f"**Source Language** `{kwargs['src']}` "
            f"[{LANGUAGES.get(translated.src, 'Auto-Detected').title()}]"
            f"\n**Destination Language** {LANGUAGES.get(translated.dest, 'Unknown').title()}"
        ).add_field(
            name="Translated Content",
            value=shorten(translated.text, 1024),
            inline=False
        )
        await ctx.send(embed=embed)

    @commands.command(name="avatar", aliases=["av", "avy", "pfp"])
    async def avatar_command(self, ctx, *, user: Union[int, mention_converter, discord.Member] = None):
        """Retrieves the avatar of yourself, or a specified user"""
        if isinstance(user, (int, type(None))):
            user = await self.bot.fetch_user(user) if user else ctx.author

        formats = ["PNG", "JPG", "WEBP"]  # I want it to be known that I *wanted* to
        if user.avatar.is_animated():     # do some weird walrus operator stuff here,
            formats.append("GIF")         # but it would be less performant
        embed = neo.Embed(
            description="**View in Browser**\n" + " • "
            .join(f"[{fmt}]({user.avatar.with_format(fmt.lower())})" for fmt in formats)
        ).set_image(url=user.avatar).set_author(name=user)

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
        flags = [v for k, v in BADGE_MAPPING.items() if k in
                 {flag.name for flag in user.public_flags.all()}]
        title = str(user)
        description = " ".join(flags) + ("\n" * bool(flags))
        description += f"**Created Account** <t:{int(user.created_at.timestamp())}:D>"

        if user.bot:
            title = ICON_MAPPING["verified_bot_tag"] if user.public_flags \
                .verified_bot else ICON_MAPPING["bot_tag"] + " " + title

        if isinstance(user, discord.Member):
            description += f"\n**Joined Server** <t:{int(user.joined_at.timestamp())}:D>"
            if user.id == ctx.guild.owner_id:
                title = "{0} {1}".format(ICON_MAPPING["guild_owner"], title)

        embed.title = title
        embed.description = description

        await ctx.send(embed=embed)

    @commands.guild_only()
    @commands.command(name="serverinfo", aliases=["si"])
    async def guild_info_command(self, ctx):
        """Retrieves information about the current server"""
        animated_emotes = len([e for e in ctx.guild.emojis if e.animated])
        static_emotes = len(ctx.guild.emojis) - animated_emotes

        embed = neo.Embed(
            title=f"{PREMIUM_ICON_MAPPING[ctx.guild.premium_tier]} {ctx.guild}",
            description=f"**Description** {ctx.guild.description}\n\n" * bool(ctx.guild.description)
            + f"**Created** <t:{int(ctx.guild.created_at.timestamp())}:D>"
            f"\n**Owner** <@{ctx.guild.owner_id}>"
            f"\n\n**Emotes** {static_emotes}/{ctx.guild.emoji_limit} static"
            f" | {animated_emotes}/{ctx.guild.emoji_limit} animated"
            f"\n**Filesize Limit** {round(ctx.guild.filesize_limit / 1_000_000)} MB"
            f"\n**Bitrate Limit** {round(ctx.guild.bitrate_limit / 1_000)} KB/s"
        ).set_thumbnail(url=ctx.guild.icon)

        await ctx.send(embed=embed)

    @commands.command(
        name="info",
        aliases=["about", "invite", "support", "source", "privacy"]
    )
    async def neo_info_command(self, ctx):
        """Show information about neo phoenix"""
        embed = neo.Embed(
            description=(
                "**neo Version** {0}"
                "\n**Server Count** {1}"
                "\n**Startup Time** <t:{2}>"
                "\n\n**Python Version** {3}"
                "\n**discord.py Version** {4}"
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
        await ctx.send(embed=embed, view=self.info_buttons())


def setup(bot):
    bot.add_cog(Utility(bot))
