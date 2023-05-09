# PDM
import emoji
from discord import (
    Cog,
    Role,
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
from tenpo.db import Action, Container
from tenpo.__main__ import DB
from tenpo.log_utils import getLogger
from tenpo.chat_utils import (
    ACTION_MAP,
    CONTAINER_MAP,
    format_reacts,
    format_channel,
    format_role_info,
    format_opens_user,
    get_discord_reacts,
    format_reacts_rules,
    format_rules_exceptions,
)

LOG = getLogger()

# can't use discord.guild.GuildChannel because it includes categories
MessageableGuildChannel = TextChannel | ForumChannel | StageChannel | VoiceChannel
DiscordContainer = Guild | CategoryChannel | MessageableGuildChannel
DiscordActor = Member | User | Guild


# TODO:: generate these functions
class CogRules(Cog):
    def __init__(self, bot):
        self.bot: commands.Bot = bot

    guild_rules = SlashCommandGroup(name="lawa_ma")

    @guild_rules.command(name="sona", description="ilo ni li ken seme? o pana e sona")
    async def guild_help(self, ctx: ApplicationContext):
        actor = ctx.guild
        assert actor
        await cmd_lawa_help(ctx, actor, ephemeral=False)

    @guild_rules.command(name="ale", description="o lukin e lawa ma")
    @commands.has_permissions(administrator=True)
    async def guild_list_rules(self, ctx: ApplicationContext):
        actor = ctx.guild
        assert actor
        await cmd_list_rules(ctx, actor, ephemeral=False)

    @guild_rules.command(name="poki", description="toki pona taso o tawa jan poki")
    @option(name="poki", description="mi lukin e poki ni taso")
    @commands.has_permissions(administrator=True)
    async def guild_toggle_role(self, ctx: ApplicationContext, poki: Role):
        actor = ctx.guild
        assert actor

        result = await DB.toggle_role(actor.id, poki.id)
        if result:
            await ctx.respond("mi lukin taso e poki __%s__" % poki.name)
            return
        await ctx.respond("mi weka e poki __%s__ la mi lukin e ale" % poki.name)

    @guild_rules.command(name="tomo_tenpo", description="mun tenpo o lon tomo seme")
    @option(name="tomo", description="tomo seme la nimi o tenpo")
    @commands.has_permissions(administrator=True)
    async def guild_toggle_calendar(
        self, ctx: ApplicationContext, tomo: MessageableGuildChannel
    ):
        actor = ctx.guild
        assert actor

        result = await DB.toggle_role(actor.id, tomo.id)
        if result:
            await ctx.respond("mi tenpo e tomo __%s__ lon kama" % tomo.name)
            return
        await ctx.respond(
            "mi kama ante ala e nimi pi tomo __%s__ la sina ken ante e ona" % tomo.name
        )

    @guild_rules.command(name="lukin", description="mi o lukin ala lukin?")
    @commands.has_permissions(administrator=True)
    async def guild_toggle_disabled(self, ctx: ApplicationContext):
        actor = ctx.guild
        assert actor
        return await cmd_toggle_disabled(ctx, actor, ephemeral=False)

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
        actor = ctx.guild
        assert actor
        await cmd_toggle_rule(ctx, actor, tomo, Container.CHANNEL, ala, ephemeral=False)

    @guild_rules.command(name="kulupu", description="o ante e lawa kulupu")
    @option(name="kulupu", description="lon kulupu seme")
    @option(name="ala", description="kulupu li ken toki ante lon ale")
    @commands.has_permissions(administrator=True)
    async def guild_toggle_category(
        self,
        ctx: ApplicationContext,
        kulupu: CategoryChannel,
        ala: bool = False,
    ):
        actor = ctx.guild
        assert actor
        await cmd_toggle_rule(
            ctx, actor, kulupu, Container.CATEGORY, ala, ephemeral=False
        )

    @guild_rules.command(name="ma", description="o ante e lawa ma")
    @commands.has_permissions(administrator=True)
    async def guild_toggle_guild(  # TODO: sucks bad
        self,
        ctx: ApplicationContext,
    ):
        actor = ctx.guild
        assert actor  # special case: server has a server rule
        await cmd_toggle_rule(ctx, actor, actor, Container.GUILD, ephemeral=False)

    """
    User rules. They're nearly identical to guild ones.
    """
    user_rules = SlashCommandGroup(name="lawa")

    @user_rules.command(name="sona", description="ilo ni li ken seme? o pana e sona")
    async def user_help(self, ctx: ApplicationContext):
        actor = ctx.user
        assert actor
        await cmd_lawa_help(ctx, actor, ephemeral=True)

    @user_rules.command(name="ale", description="o lukin e lawa sina")
    async def user_list_rules(self, ctx: ApplicationContext):
        actor = ctx.user
        assert actor
        await cmd_list_rules(ctx, actor, ephemeral=True)

    @user_rules.command(name="lukin", description="mi o lukin ala lukin?")
    async def user_toggle_disabled(self, ctx: ApplicationContext):
        actor = ctx.user
        assert actor
        return await cmd_toggle_disabled(ctx, actor, ephemeral=True)

    @user_rules.command(name="tomo", description="o ante e lawa tomo")
    @option(name="tomo", description="lon tomo seme")
    @option(name="ala", description="tomo li ken toki pona ala lon ale")
    async def user_toggle_channel(
        self,
        ctx: ApplicationContext,
        tomo: MessageableGuildChannel,
        ala: bool = False,
    ):
        actor = ctx.user
        assert actor
        await cmd_toggle_rule(ctx, actor, tomo, Container.CHANNEL, ala, ephemeral=True)

    @user_rules.command(name="kulupu", description="o ante e lawa kulupu")
    @option(name="kulupu", description="lon kulupu seme")
    @option(name="ala", description="kulupu li ken toki ante lon ale")
    async def user_toggle_category(
        self,
        ctx: ApplicationContext,
        kulupu: CategoryChannel,
        ala: bool = False,
    ):
        actor = ctx.user
        assert actor
        await cmd_toggle_rule(
            ctx, actor, kulupu, Container.CATEGORY, ala, ephemeral=True
        )

    @user_rules.command(name="ma", description="o ante e lawa ma")
    async def user_toggle_guild(
        self,
        ctx: ApplicationContext,
    ):
        actor = ctx.user
        assert actor
        await cmd_toggle_rule(ctx, actor, ctx.guild, Container.GUILD, ephemeral=True)

    @user_rules.command(
        name="open", description="open pi toki sina li ni la mi lukin ala"
    )
    @option(name="toki", description="toki open")
    async def user_toggle_opens(self, ctx: ApplicationContext, toki: str):
        user = ctx.user
        assert user
        result = await DB.toggle_open(user.id, toki)
        if not result:
            await ctx.respond(
                "open pi toki sina li ni la mi lukin ala: __%s__" % toki, ephemeral=True
            )
            return
        await ctx.respond("mi kama lukin e toki open ni: __%s__" % toki, ephemeral=True)

    @user_rules.command(
        name="sitelen", description="sina toki pona ala la mi pana e sitelen seme"
    )
    @option(name="sitelen", description="sitelen")
    async def user_manage_reacts(self, ctx: ApplicationContext, sitelen: str = ""):
        # TODO: split in case guild may want to configure later
        user = ctx.user
        assert user

        if not sitelen:
            await DB.set_reacts(user.id, [])
            await ctx.respond(
                "sina pana e sitelen ala la mi weka e sitelen ale", ephemeral=True
            )
            return

        emojis = [e["emoji"] for e in emoji.emoji_list(sitelen)]
        reacts = get_discord_reacts(sitelen)
        all_reacts = emojis + reacts
        if not all_reacts:
            await ctx.respond(
                "sina pana e sitelen, taso mi sona ala e ona. ona li pona ala pona?",
                ephemeral=True,
            )
            return
        await DB.set_reacts(user.id, all_reacts)

        formatted_reacts = format_reacts(all_reacts)
        await ctx.respond(
            "sina toki pona ala la mi pana e sitelen wan pi ni ale:\n%s"
            % formatted_reacts,
            ephemeral=True,
        )


async def cmd_toggle_rule(
    ctx: ApplicationContext,
    actor: DiscordActor,
    container: DiscordContainer,
    ctype: Container,
    exception: bool = False,
    ephemeral: bool = False,
):
    guild = ctx.guild
    assert guild
    user = ctx.user
    assert user

    action = await DB.toggle_rule(container.id, ctype, actor.id, exception)
    response = await build_rule_resp(container, ctype, action, exception)
    await ctx.respond(response, ephemeral=ephemeral)


async def cmd_toggle_disabled(
    ctx: ApplicationContext, actor: DiscordActor, ephemeral: bool
):
    result = await DB.toggle_disabled(actor.id)
    resp = "mi kama lukin ala" if result else "mi kama lukin"
    await ctx.respond(resp, ephemeral=ephemeral)


async def build_rule_resp(
    container: DiscordContainer,
    ctype: Container,
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


# TODO: for following two funcs, better division of user|guild behavior?


async def cmd_list_rules(ctx: ApplicationContext, actor: DiscordActor, ephemeral: bool):
    guild = ctx.guild
    assert guild
    user = ctx.user
    assert user

    is_guild = isinstance(actor, Guild)

    blurbs = []

    disabled = await DB.get_disabled(actor.id)
    if disabled:
        disabled_info = "**mi lukin ala e toki sina. lawa li lon tawa sona.**"
        blurbs.append(disabled_info)

    rules, exceptions = await DB.list_rules(actor.id)
    rules_info = format_rules_exceptions(rules, exceptions)
    blurbs.append(rules_info)

    if not is_guild:
        reacts = await DB.get_reacts(actor.id)
        reacts_info = format_reacts_rules(reacts)
        blurbs.append(reacts_info)

        opens = await DB.get_opens(actor.id)
        opens_info = format_opens_user(opens)
        blurbs.append(opens_info)

    if is_guild:
        role_id = await DB.get_role(actor.id)
        role = guild.get_role(role_id)
        if role:  # safety check in case configured role is deleted
            role_info = format_role_info(role.name)
            blurbs.append(role_info)

    result = "\n\n".join(blurbs)  # TODO: best order?
    await ctx.respond(result, ephemeral=ephemeral)


async def cmd_lawa_help(ctx: ApplicationContext, actor: DiscordActor, ephemeral: bool):
    guild = ctx.guild
    assert guild
    user = ctx.user
    assert user

    is_guild = isinstance(actor, Guild)

    prefix = "/lawa"
    if is_guild:
        prefix = "/lawa_ma"

    sona = "mi __ilo pi toki pona taso__. sina toki pona ala la mi pona e ona. o lukin e ken mi:\n"

    sona += f"`{prefix} sona`: mi pana e toki ni.\n"
    sona += f"`{prefix} ale`: mi pana e lawa ale sina.\n"
    sona += f"`{prefix} lukin`: mi lukin ala. sin la mi lukin.\n"
    sona += f"`{prefix} [tomo|kulupu|ma] (ala)`: mi lukin e ijo.\n"
    sona += f"    `-` sina toki pona ala lon ijo la mi pona e ona.\n"
    sona += f"    `-` `ala` la mi lukin ala e ijo. ijo ni li ken lon insa pi ijo pi toki pona.\n"
    sona += f"    `-` sina pana tu e ijo sama la mi weka e lukin.\n"
    if not is_guild:
        sona += f"`{prefix} open [toki]`: toki li lon open pi toki sina la mi lukin ala e ona.\n"
        sona += f"    - sina pana tu e toki sama la mi weka e ona.\n"
        sona += (
            f"`{prefix} sitelen [sitelen]`: sina toki pona ala la mi pana e sitelen.\n"
        )
        sona += f"`{prefix} weka [True|False]`: sina toki pona ala la mi weka e toki. sina wile ala e weka la\n"
    if is_guild:
        sona += f"`{prefix} poki [poki]`: sina pana e poki tawa ma la mi lukin taso e jan pi poki ni.\n"
    await ctx.respond(sona, ephemeral=ephemeral)
