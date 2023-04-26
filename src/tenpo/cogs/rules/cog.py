# STL
from typing import List, Tuple

# PDM
import emoji
from discord import (
    Cog,
    User,
    Guild,
    Member,
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
from tenpo.log_utils import getLogger
from tenpo.chat_utils import (
    ACTION_MAP,
    CONTAINER_MAP,
    format_reacts,
    format_channel,
    get_discord_reacts,
    format_reacts_rules,
    format_rules_exceptions,
)

LOG = getLogger()

# can't use discord.guild.GuildChannel because it includes categories
MessageableGuildChannel = TextChannel | ForumChannel | StageChannel | VoiceChannel
DiscordContainer = Guild | CategoryChannel | MessageableGuildChannel



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
        await list_rules(ctx, Owner.GUILD)

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
        await list_rules(ctx, Owner.USER)

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

    # user_open = user_rules.create_subgroup(
    #     name="open", description="mi o lukin ala e toki pi open seme"
    # )
    #
    # @user_open.command(name="pana", description="ilo o lukin ala e toki open seme")
    # @option(name="toki", description="toki open")
    # async def user_add_prefix(self, ctx: ApplicationContext, toki: str):
    #     pass
    #
    # @user_open.command(name="weka", description="")
    # @option(name="", description="mi weka e sitelen seme")
    # async def user_delete_prefix(self, ctx: ApplicationContext, toki: str):
    #     pass

    @user_rules.command(
        name="sitelen", description="sina toki pona ala la mi pana e sitelen seme"
    )
    @option(name="sitelen", description="sitelen")
    async def user_manage_reacts(self, ctx: ApplicationContext, sitelen: str = ""):
        user = ctx.user
        assert user

        if not sitelen:
            await DB.set_reacts(user.id, Owner.USER, [])
            await ctx.respond("sina pana e sitelen ala la mi weka e sitelen ale")
            return

        emojis = [e["emoji"] for e in emoji.emoji_list(sitelen)]
        reacts = get_discord_reacts(sitelen)
        all_reacts = emojis + reacts
        if not all_reacts:
            await ctx.respond(
                "sina pana e sitelen, taso mi sona ala e ona. ona li pona ala pona?"
            )
            return
        await DB.set_reacts(user.id, Owner.USER, all_reacts)

        if __debug__:
            reacts = await DB.get_reacts(user.id, Owner.USER)
            LOG.debug(reacts)

        formatted_reacts = format_reacts(all_reacts)
        await ctx.respond(
            "sina toki pona ala la mi pana e sitelen wan pi ni ale:\n%s"
            % formatted_reacts
        )


def owner_resp_coalesce(
    otype: Owner, user: User | Member, guild: Guild
) -> Tuple[User | Member | Guild, bool]:
    if otype == Owner.USER:
        owner = user
        ephemeral = True
    elif otype == Owner.GUILD:
        owner = guild
        ephemeral = False
    return owner, ephemeral


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

    owner, ephemeral = owner_resp_coalesce(otype, user, guild)

    action = await DB.toggle_rule(container.id, ctype, owner.id, otype, exception)
    response = await build_rule_resp(container, ctype, otype, action, exception)
    await ctx.respond(response, ephemeral=ephemeral)


async def build_rule_resp(
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


async def list_rules(ctx: ApplicationContext, otype: Owner):
    guild = ctx.guild
    assert guild
    user = ctx.user
    assert user

    owner, ephemeral = owner_resp_coalesce(otype, user, guild)

    rules, exceptions = await DB.list_rules(owner.id, otype)
    rules_info = format_rules_exceptions(rules, exceptions)

    reacts = await DB.get_reacts(owner.id, otype)
    reacts_info = format_reacts_rules(reacts)

    result = rules_info + "\n\n" + reacts_info

    await ctx.respond(result, ephemeral=ephemeral)


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
/lawa sitelen [sitelen]: sina toki pona ala la mi pana e sitelen.
/lawa weka [True|False]: sina toki pona ala la mi weka e toki. sina wile ala e weka la
    """
    await ctx.respond(sona)
