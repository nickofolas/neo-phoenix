import fubuki
from discord.ext import commands
from fubuki.modules import Paginator, args, cse, dictionary


def _result_to_embed(result):
    embed = fubuki.Embed(
        title=result.title,
        description=result.snippet,
        url=result.url
    )
    embed.set_image(url=result.image_url or '')
    return embed


def _definitions_to_embed(word):
    for meaning in word.meanings:
        for definition in meaning.definitions:
            embed = fubuki.Embed(
                description=definition.definition
            ).set_author(
                name=f'{word.word}: {meaning.part_of_speech}'
            ).add_field(
                name="Synonyms",
                value=', '.join((definition.synonyms or ['No synonyms'])[:5])
            )
            yield embed


class Utility(fubuki.Addon):
    def __init__(self, bot):
        self.bot = bot
        self.google = cse.Search(
            key=bot.cfg['bot']['cse_keys'],
            engine_id=bot.cfg['bot']['cse_engine'],
            session=bot.session
        )
        self.dictionary = dictionary.Define(bot.session)

    @args.add_arg(
        "query",
        nargs="*",
        help="The query which will searched for on Google"
    )
    @args.add_arg(
        '-i', '--image',
        action='store_true',
        help="Toggles whether or not Google Images will be searched"
    )
    @args.command(name='google', aliases=['g'])
    async def google_command(self, ctx, *, query):
        resp = await self.google.search(
            ' '.join(query.query),
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
    @args.command(name='define')
    async def dictionary_command(self, ctx, *, query):
        """Search the dictionary for a word's definition."""
        resp = await self.dictionary.define(
            ' '.join(query.word),
            lang_code=query.lang_code
        )

        embeds = []
        for word in resp.words:
            embeds.extend(_definitions_to_embed(word))
        if not embeds:
            return await ctx.send("No definition found")

        menu = Paginator.from_embeds(embeds)
        await menu.start(ctx)


def setup(bot):
    bot.add_cog(Utility(bot))
