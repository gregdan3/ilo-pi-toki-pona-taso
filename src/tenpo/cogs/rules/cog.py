# STL
import logging

# PDM
from discord import (
    Cog,
    Guild,
    TextChannel,
    ForumChannel,
    StageChannel,
    VoiceChannel,
    CategoryChannel,
    SlashCommandGroup,
    option,
)
from discord.ext import commands
from discord.commands.context import ApplicationContext

# LOCAL
from tenpo.db import Owner, Action, Container
from tenpo.__main__ import DB, TenpoBot

# can't use discord.guild.GuildChannel because it includes categories
MessageableGuildChannel = TextChannel | ForumChannel | StageChannel | VoiceChannel
DiscordContainer = Guild | CategoryChannel | MessageableGuildChannel


LOG = logging.getLogger("tenpo")


CONTAINER_MAP = {
    Container.CHANNEL: "tomo",
    Container.CATEGORY: "kulupu",
    Container.GUILD: "ma",
}
ACTION_MAP = {
    Action.INSERT: "pana",
    Action.UPDATE: "ante",
    Action.DELETE: "weka",
}


def format_channel(id: int):
    """categories are channels according to pycord and they use the same escape"""
    return f"<#{id}>"


def format_guild(id: int):
    # NOTE: i hope they add something better than this
    return f"<https://discord.com/channels/{id}>"


def format_rules(rules, prefix):
    rules_str = prefix + ": \n"
    for val in Container:
        if not rules[val]:
            continue

        rules_str += "  " + CONTAINER_MAP[val] + "\n"
        formatter = format_channel
        if val == Container.GUILD:
            formatter = format_guild

        for rule in rules[val]:
            rules_str += "    " + formatter(rule) + "\n"

    return rules_str


def format_rules_exceptions(rules: dict, exceptions: dict):
    resp = ""
    if rules:
        frules = format_rules(rules, "ni o toki pona taso")
        resp += frules
        resp += "\n"
    if exceptions:
        fexcepts = format_rules(exceptions, "ni li ken toki ale")
        resp += fexcepts
    return resp


# TODO:: generate these functions
class CogRules(Cog):
    def __init__(self, bot):
        self.bot: TenpoBot = bot

    guild_rules = SlashCommandGroup(name="lawa_ma")

    @guild_rules.command(name="sona", description="ilo ni li ken seme? o pana e sona")
    async def guild_help(self, ctx: ApplicationContext):
        return lawa_help(ctx)

    @guild_rules.command(name="ale", description="o lukin e lawa ma")
    @commands.has_permissions(administrator=True)
    async def guild_list_rules(self, ctx: ApplicationContext):
        guild = ctx.guild
        assert guild
        rules, exceptions = await DB.list_rules(guild.id, Owner.GUILD)
        formatted = format_rules_exceptions(rules, exceptions)
        await ctx.respond(formatted)

    @guild_rules.command(name="tomo", description="o ante e lawa tomo")
    @option(name="tomo", description="lon tomo seme")
    @option(name="ala", description="tomo li ken toki ante lon ale")
    @commands.has_permissions(administrator=True)
    async def guild_toggle_channel(
        self,
        ctx: ApplicationContext,
        tomo: MessageableGuildChannel,
        ala: bool = False,
    ):
        await cmd_toggle_rule(ctx, tomo, Container.CHANNEL, Owner.GUILD, ala)

    @guild_rules.command(name="kulupu", description="o ante e lawa kulupu")
    @option(name="kulupu", description="lon kulupu seme")
    @option(name="ala", description="kulupu li ken toki ante lon ale")
    @commands.has_permissions(administrator=True)
    async def guild_toggle_category(
        self,
        ctx: ApplicationContext,
        kulupu: MessageableGuildChannel,
        ala: bool = False,
    ):
        await cmd_toggle_rule(ctx, kulupu, Container.CATEGORY, Owner.GUILD, ala)

    @guild_rules.command(name="ma", description="o ante e lawa ma")
    @commands.has_permissions(administrator=True)
    async def guild_toggle_guild(  # TODO: sucks bad
        self,
        ctx: ApplicationContext,
    ):
        await cmd_toggle_rule(ctx, ctx.guild, Container.GUILD, Owner.GUILD)

    """
    User rules. They're nearly identical to guild ones.
    """
    user_rules = SlashCommandGroup(name="lawa")

    @user_rules.command(name="sona", description="ilo ni li ken seme? o pana e sona")
    async def user_help(self, ctx: ApplicationContext):
        return lawa_help(ctx)

    @user_rules.command(name="ale", description="o lukin e lawa sina")
    async def user_list_rules(self, ctx: ApplicationContext):
        guild = ctx.guild
        assert guild
        user = ctx.user
        assert user

        rules, exceptions = await DB.list_rules(user.id, Owner.USER)
        formatted = format_rules_exceptions(rules, exceptions)
        await ctx.respond(formatted, ephemeral=True)

    @user_rules.command(name="tomo", description="o ante e lawa tomo")
    @option(name="tomo", description="lon tomo seme")
    @option(name="ala", description="tomo li ken toki pona ala lon ale")
    async def user_toggle_channel(
        self,
        ctx: ApplicationContext,
        tomo: MessageableGuildChannel,
        ala: bool = False,
    ):
        await cmd_toggle_rule(ctx, tomo, Container.CHANNEL, Owner.USER, ala)

    @user_rules.command(name="kulupu", description="o ante e lawa kulupu")
    @option(name="kulupu", description="lon kulupu seme")
    @option(name="ala", description="kulupu li ken toki ante lon ale")
    async def user_toggle_category(
        self,
        ctx: ApplicationContext,
        kulupu: CategoryChannel,
        ala: bool = False,
    ):
        await cmd_toggle_rule(ctx, kulupu, Container.CATEGORY, Owner.USER, ala)

    @user_rules.command(name="ma", description="o ante e lawa ma")
    async def user_toggle_guild(
        self,
        ctx: ApplicationContext,
    ):
        await cmd_toggle_rule(ctx, ctx.guild, Container.GUILD, Owner.USER)

    @user_rules.command(name="open", description="ilo o lukin ala e toki open seme")
    @option(name="toki", description="toki open")
    async def user_manage_prefix(self, ctx: ApplicationContext, toki: str):
        pass

    @user_rules.command(
        name="sitelen", description="sina toki pona ala la mi seme e toki"
    )
    @option(name="sitelen", description="")
    async def user_manage_emojis(self, ctx: ApplicationContext, sitelen: str):
        pass


async def cmd_toggle_rule(
    ctx: ApplicationContext,
    container: DiscordContainer,
    ctype: Container,
    otype: Owner,  # owner object isn't needed if we have context and otype
    exception: bool = False,
):
    guild = ctx.guild
    assert guild
    user = ctx.user
    assert user

    if otype == Owner.USER:
        owner = user
        ephemeral = True
    elif otype == Owner.GUILD:
        owner = guild
        ephemeral = False

    action = await DB.toggle_rule(container.id, ctype, owner.id, otype, exception)
    response = await build_response(container, ctype, otype, action, exception)
    await ctx.respond(response, ephemeral=ephemeral)


async def build_response(
    container: DiscordContainer,
    ctype: Container,
    otype: Owner,
    action: Action,
    exception: bool,
):
    container_ = CONTAINER_MAP[ctype]
    verb = ACTION_MAP[action]
    formatted = (
        format_channel(container.id)
        if ctype != Container.GUILD
        else f"__{container.name}__"  # TODO: formatting guilds in different ways
        # NOTE: I could just say "ni" instead of getting all fancy
    )

    result = ""
    if action in (Action.INSERT, Action.UPDATE):
        if exception:
            result += "ona li ken toki ale."
        else:
            result += "ona o toki pona taso."

    response = f"{container_} {formatted} la mi {verb} e lawa. {result}"
    return response


async def lawa_help(ctx: ApplicationContext):
    sona = """mi __ilo pi toki pona taso__. sina toki pona ala la mi pana e sona pakala.
/lawa sona: mi pana e toki ni.

lawa la mi lukin pona e toki sina.
mi ken ni lon **tomo** lon **kulupu** tomo lon **ma**.

sina lawa wan e ijo la mi lukin e ona.
sina lawa tu e ijo sama la mi weka e lukin.

/lawa ale: o lukin e lawa ale sina.
/lawa [tomo|kulupu|ma] (ala): mi lukin e ijo.
    - ala la mi lukin ala e ijo. ni li ken lon kulupu pi toki pona lon ma pi toki pona.
    - sina lawa tu e ijo sama la mi weka e lukin.

/lawa open [toki]: toki li lon open pi toki sina la mi lukin ala e ona.
/lawa sitelen: sina toki pona ala la mi pana e sitelen.
/lawa weka [True|False]: sina toki pona ala la mi weka e toki. sina wile ala e weka la
    """
    await ctx.respond(sona)
