from collections import defaultdict
from dataclasses import dataclass
from operator import attrgetter
from textwrap import shorten

import discord
import neo
from discord.ext import commands
from discord.utils import escape_markdown
from neo.modules import Paginator
from neo.tools import is_registered_profile


@dataclass
class TodoItem:
    user_id: int
    content: str
    guild_id: str
    channel_id: int
    message_id: int
    edited: bool

    def __repr__(self):
        return "<{0.__class__.__name__} user_id={0.user_id} message_id={0.message_id}>".format(self)

    @property
    def jump_url(self):
        return 'https://discord.com/channels/{0.guild_id}/{0.channel_id}/{0.message_id}'.format(self)

    @property
    def created_at(self):
        return discord.utils.snowflake_time(self.message_id)


class Todos(neo.Addon):
    """Commands for managing a todo list"""

    def __init__(self, bot):
        self.bot = bot
        self.todos = defaultdict(list)

        self.bot.loop.create_task(self.__ainit__())

    async def __ainit__(self):
        await self.bot.wait_until_ready()

        for record in await self.bot.db.fetch("SELECT * FROM todos"):
            self.todos[record["user_id"]].append(TodoItem(**record))

    # Need to dynamically account for deleted profiles
    @commands.Cog.listener("on_profile_delete")
    async def handle_deleted_profile(self, user_id: int):
        self.todos.pop(user_id, None)

    async def cog_check(self, ctx):
        return await is_registered_profile().predicate(ctx)

    @commands.group(invoke_without_command=True)
    async def todo(self, ctx):
        """List your todos"""
        formatted_todos = []

        for index, todo in enumerate(self.todos[ctx.author.id], 1):
            formatted_todos.append("`{0}` {1}".format(
                index, escape_markdown(shorten(todo.content, width=75))
            ))

        menu = Paginator.from_iterable(
            formatted_todos or ["No todos"],
            per_page=10,
            use_embed=True
        )
        await menu.start(ctx)

    @todo.command(name="add")
    async def todo_add(self, ctx, *, content: str):
        """Add a new todo"""
        data = {
            "user_id": ctx.author.id,
            "content": content,
            "guild_id": str(getattr(ctx.guild, "id", "@me")),
            "channel_id": ctx.channel.id,
            "message_id": ctx.message.id,
            "edited": False
        }

        await self.bot.db.execute(
            """
            INSERT INTO todos (
                user_id,
                content,
                guild_id,
                channel_id,
                message_id,
                edited
            ) VALUES (
                $1, $2, $3, $4, $5, $6
            )
            """,
            *data.values()
        )

        self.todos[ctx.author.id].append(TodoItem(**data))
        await ctx.message.add_reaction("\U00002611")

    @todo.command(name="remove", aliases=["rm"])
    async def todo_remove(self, ctx, *indices):
        """
        Remove 1 or more todo by index

        Passing `~` will remove all todos at once
        """
        if "~" in indices:
            todos = self.todos[ctx.author.id].copy()
            self.todos[ctx.author.id].clear()

        else:
            (indices := [*map(str, indices)]).sort(reverse=True)  # Pop in an way that preserves the list's original order
            try:
                todos = [self.todos[ctx.author.id].pop(index - 1) for index in map(
                    int, filter(str.isdigit, indices))
                ]
            except IndexError:
                raise IndexError("One or more of the provided indices is invalid.")

        await self.bot.db.execute(
            """
            DELETE FROM todos WHERE
                message_id=ANY($1::BIGINT[]) AND
                user_id=$2
            """,
            [*map(attrgetter("message_id"), todos)],
            ctx.author.id
        )
        await ctx.message.add_reaction("\U00002611")

    @todo.command(name="view", aliases=["show"])
    async def todo_view(self, ctx, index: int):
        """View a todo by its listed index"""
        try:
            todo: TodoItem = self.todos[ctx.author.id][index - 1]
        except IndexError:
            raise IndexError("Couldn't find that todo.")

        embed = neo.Embed(
            description=todo.content
        ).add_field(
            name=f"Created on <t:{int(todo.created_at.timestamp())}>",
            value=f"[Jump to origin]({todo.jump_url})"
        ).set_author(
            name="Viewing a todo {}".format(
                "[edited]" if todo.edited else ""
            ),
            icon_url=ctx.author.avatar
        )

        await ctx.send(embed=embed)

    @todo.command(name="edit")
    async def todo_edit(self, ctx, index: int, *, new_content: str):
        """Edit the content of a todo"""
        try:
            todo: TodoItem = self.todos[ctx.author.id][index - 1]
        except IndexError:
            raise IndexError("Couldn't find that todo.")

        todo.content = new_content
        todo.edited = True
        await self.bot.db.execute(
            """
            UPDATE todos
            SET
                content=$1,
                edited=TRUE
            WHERE
                message_id=$2 AND
                user_id=$3
            """,
            new_content, todo.message_id, todo.user_id
        )
        await ctx.message.add_reaction("\U00002611")


def setup(bot):
    bot.add_cog(Todos(bot))
