from typing import Union

import discord
import neo
from dateutil.relativedelta import relativedelta
from discord.ext import commands
from neo.modules import Paginator, args, cse, dictionary
from neo.types.converters import MentionConverter

DELTA_FORMAT = "{0.months} months and {0.days} days ago"
ACTIVITY_TYPE_MAPPING = {
    discord.ActivityType.watching: "Watching",
    discord.ActivityType.playing: "Playing",
    discord.ActivityType.streaming: "Streaming",
    discord.ActivityType.listening: "Listening to",
    discord.ActivityType.competing: "Competing in",
}
ACTIVITY_MAPPING = {
    discord.Spotify: "Listening to **{0}**",
    discord.Game: "Playing **{0}**",
    discord.Streaming: "Streaming **{0}**"
}
STATUS_ICON_MAPPING = {
    "online": "<:online:743228917279752202>",
    "dnd": "<:dnd:743228917619490826>",
    "idle": "<:idle:743228917589999678>",
    "offline": "<:offline:743228917279621221>"
}
BADGE_ICON_MAPPING = {
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


class Utility(neo.Addon):
    """Various utility commands"""

    def __init__(self, bot):
        self.bot = bot

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

    @args.add_arg(
        "query",
        nargs="*",
        help="The query which will searched for on Google"
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
            return await ctx.send("Search returned no results")

        menu = Paginator.from_embeds(embeds)
        await menu.start(ctx)

    @args.add_arg(
        "word",
        nargs="*",
        help="The word to search a dictionary for"
    )
    @args.add_arg(
        "-lc", "--lang_code",
        nargs="?",
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
            return await ctx.send("No definition found")

        menu = Paginator.from_embeds(embeds)
        await menu.start(ctx)

    @commands.command(name="avatar", aliases=["av"])
    async def avatar_command(self, ctx, *, user: Union[int, MentionConverter] = None):
        """Retrieves the avatar of yourself, or a specified user"""

        user = await self.bot.fetch_user(user) if user else ctx.author
        url = user.avatar_url

        embed = neo.Embed(
            description=f"[View in browser]({url})"
        ).set_image(url=url).set_footer(text=str(user))

        await ctx.send(embed=embed)

    # TODO: Display bot tags and owner crowns
    @commands.command(name="userinfo", aliases=["ui"])
    async def userinfo_command(self, ctx, *, user: Union[discord.Member, int, MentionConverter] = None):
        """Retrieves information of yourself, or a specified user"""

        user = user or ctx.author
        if not isinstance(user, discord.Member):
            user = await self.bot.fetch_user(user)

        else:
            joined_ago = relativedelta(ctx.message.created_at, user.joined_at)

        created_ago = relativedelta(ctx.message.created_at, user.created_at)

        embed = neo.Embed().set_thumbnail(url=user.avatar_url)

        flags = [BADGE_ICON_MAPPING[pair[0]] for pair in user.public_flags if pair[1]]
        title = str(user)
        description = " ".join(flags) + ("\n" if flags else "")
        description += "**Created** " + DELTA_FORMAT.format(created_ago)

        if isinstance(user, discord.Member):
            title = f"{STATUS_ICON_MAPPING[user.raw_status]} {title}"

            description += "\n**Joined** " + DELTA_FORMAT.format(joined_ago)
            # description += "\n**Join Position** {}".format(
            #     sorted(ctx.guild.members, key=lambda m: m.joined_at).index(user) + 1
            # )  # This is currently commented out for aesthetic reasons lmao

            activities = []
            for activity in user.activities:
                if (act := ACTIVITY_MAPPING.get(type(activity))):
                    activities.append(act.format(activity.name))  # For stuff like Spotify

                elif isinstance(activity, discord.activity.Activity):
                    activities.append("{0} **{1.name}**".format(
                        ACTIVITY_TYPE_MAPPING.get(activity.type), activity)
                    )  # For more ambiguous status types

                elif isinstance(activity, discord.CustomActivity):
                    if not activity.emoji:
                        emoji = ""
                    elif activity.emoji.is_unicode_emoji() or activity.emoji in self.bot.emojis:
                        emoji = activity.emoji
                    else:
                        emoji = ":question:"
                    activities.append(f"{emoji} {activity.name}")

            if activities:
                embed.add_field(
                    name="Activities",
                    value="\n".join(activities)
                )

        embed.title = title
        embed.description = description

        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Utility(bot))
