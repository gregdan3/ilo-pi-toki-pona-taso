# STL
import logging

# PDM
from discord import Cog, ForumChannel, CategoryChannel, SlashCommandGroup, option
from __main__ import TenpoBot
from discord.ext import commands
from discord.channel import TextChannel
from discord.types.channel import Channel
from discord.commands.context import ApplicationContext

# LOCAL
from tenpo.__main__ import DB

LOG = logging.getLogger("tenpo")

# LOCAL
from tenpo.db import Owner, Container


def format_link(id: int):
    return f"<#{id}>"


def format_rules(rules, prefix):
    rules_str = prefix + ": \n"
    for val in Container:
        if val not in rules:
            continue
            # TODO: unite handling of user/guild rules? maybe guilds should just always give an empty guild
        if not rules[val]:
            continue

        # TODO: map container names into toki pona

        rules_str += "  " + val.value + "\n"

        for rule in rules[val]:
            rules_str += "    " + format_link(rule) + "\n"

    return rules_str


def format_rules_exceptions(rules, exceptions):
    frules = format_rules(rules, "lawa")
    fexcepts = format_rules(exceptions, "lawa ala")
    return frules + "\n" + fexcepts


class CogRules(Cog):
    def __init__(self, bot):
        self.bot: TenpoBot = bot

    guild_rules = SlashCommandGroup(name="lawa_ma")
    guild_channel = guild_rules.create_subgroup("tomo")
    guild_category = guild_rules.create_subgroup("kulupu")

    user_rules = SlashCommandGroup(name="lawa")
    user_channel = user_rules.create_subgroup("tomo")
    user_category = user_rules.create_subgroup("kulupu")
    user_guild = user_rules.create_subgroup("ma")

    # TODO:
    # yes I can generate these but I lose the niceness of typing and hand-picked descriptions/settings for each option
    # but also the descriptions are so similar that they should be abstracted out

    @guild_rules.command(name="ale", description="o lukin e lawa ale lon ma")
    @commands.has_permissions(administrator=True)
    async def guild_list_rules(self, ctx: ApplicationContext):
        guild = ctx.guild
        assert guild
        rules, exceptions = await DB.list_guild_rules(guild.id)
        formatted = format_rules_exceptions(rules, exceptions)
        await ctx.respond(formatted)

    @guild_channel.command(name="pana", description="o toki pona taso e tomo anu ala")
    @option(name="tomo", description="tomo ni o toki pona taso anu ala")
    @option(
        name="ala",
        description="ala la tomo li ken toki pona ala. kulupu tomo li suli ala.",
    )
    @commands.has_permissions(administrator=True)
    async def guild_add_channel(
        self,
        ctx: ApplicationContext,
        tomo: TextChannel | ForumChannel,
        ala: bool = False,
    ):
        guild = ctx.guild
        assert guild
        await add_rule(tomo.id, Container.CHANNEL, guild.id, Owner.GUILD, ala)
        if ala:  # TODO: respond to db state more clearly
            await ctx.respond(f"tomo <#{tomo.id}> li ken toki pona ala")
        else:
            await ctx.respond(f"tomo <#{tomo.id}> o toki pona taso")

    @guild_channel.command(name="weka", description="o weka e toki pona taso tan tomo")
    @option(name="tomo", description="tomo ni li ken toki pona ala")
    @commands.has_permissions(administrator=True)
    async def guild_remove_channel(
        self, ctx: ApplicationContext, tomo: TextChannel | ForumChannel
    ):
        guild = ctx.guild
        assert guild
        await remove_rule(tomo.id, Container.CHANNEL, guild.id, Owner.GUILD)
        await ctx.respond(f"tomo <#{tomo.id}> li ken toki pona ala")

    @guild_category.command(name="pana", description="o toki pona taso e kulupu tomo")
    @option(name="kulupu", description="kulupu tomo ni o toki pona taso")
    @commands.has_permissions(administrator=True)
    async def guild_add_category(
        self, ctx: ApplicationContext, kulupu: CategoryChannel
    ):
        guild = ctx.guild
        assert guild
        assert isinstance(kulupu, CategoryChannel)
        await add_rule(kulupu.id, Container.CATEGORY, guild.id, Owner.GUILD)
        await ctx.respond(f"kulupu tomo <#{kulupu.id}> o toki pona taso")

    @guild_category.command(
        name="weka", description="o weka e toki pona taso tan kulupu tomo"
    )
    @option(name="kulupu", description="kulupu tomo ni li ken toki pona ala")
    async def guild_remove_category(
        self, ctx: ApplicationContext, kulupu: CategoryChannel
    ):
        guild = ctx.guild
        assert guild
        assert isinstance(kulupu, CategoryChannel)
        await remove_rule(kulupu.id, Container.CATEGORY, guild.id, Owner.GUILD)
        await ctx.respond(f"kulupu tomo <#{kulupu.id}> li ken toki pona ala")


async def add_rule(
    entity_id: int,
    ctype: Container,
    owner_id: int,
    owner_type: Owner,
    exception: bool = False,
):
    if owner_type == Owner.USER:
        await DB.insert_user_rule(
            id=entity_id,
            user_id=owner_id,
            ctype=ctype,
            exception=exception,
        )
    elif owner_type == Owner.GUILD:
        await DB.insert_guild_rule(
            id=entity_id,
            guild_id=owner_id,
            ctype=ctype,
            exception=exception,
        )
    else:
        raise ValueError("No such owner_type %s", owner_type)


async def remove_rule(
    entity_id: int,
    ctype: Container,
    owner_id: int,
    owner_type: Owner,
):
    if owner_type == Owner.USER:
        await DB.delete_user_rule(id=entity_id, user_id=owner_id, ctype=ctype)
    elif owner_type == Owner.GUILD:
        await DB.delete_guild_rule(id=entity_id, guild_id=owner_id, ctype=ctype)
    else:
        raise ValueError("No such owner_type %s", owner_type)
