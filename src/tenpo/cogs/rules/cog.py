# STL
import re
from typing import Literal, cast

# PDM
import emoji
from discord import Cog, Role, Guild, CategoryChannel, SlashCommandGroup, option
from discord.ext import commands
from discord.commands.context import ApplicationContext

# LOCAL
from tenpo.db import Pali, IjoSiko
from tenpo.types import DiscordActor, DiscordContainer, MessageableGuildChannel
from tenpo.__main__ import DB
from tenpo.constants import NASIN_PI_MA_ILO, NANPA_PI_JAN_PALI
from tenpo.log_utils import getLogger
from tenpo.str_utils import (
    PALI_MAP,
    BANNED_REACTS,
    CONTAINER_MAP,
    format_reacts,
    format_channel,
    format_cron_data,
    format_role_info,
    format_opens_user,
    format_date_ranges,
    format_timing_data,
    get_discord_reacts,
    format_reacts_rules,
    format_rules_exceptions,
    format_reacts_management,
    format_removed_role_info,
)
from tenpo.croniter_utils import EventTimer, InvalidEventTimer

LOG = getLogger()

LukinOptions = Literal["lukin", "ala"]


# TODO: generate these functions
class CogRules(Cog):
    def __init__(self, bot):
        self.bot: commands.Bot = bot

    guild_rules = SlashCommandGroup(name="lawa_ma")

    @guild_rules.command(name="sona", description="ilo ni li ken seme? o pana e sona")
    async def guild_help(self, ctx: ApplicationContext):
        actor = ctx.guild
        assert actor
        await cmd_lawa_help(ctx, actor, ephemeral=True)

    @guild_rules.command(name="ale", description="ma ni la lawa li seme?")
    async def guild_list_rules(self, ctx: ApplicationContext):
        actor = ctx.guild
        assert actor
        await cmd_list_rules(ctx, actor, ephemeral=True)

    @guild_rules.command(name="weka", description="o weka e lawa ale ma")
    async def guild_delete_rules(self, ctx: ApplicationContext):
        actor = ctx.guild
        assert actor
        await cmd_delete_rules(ctx, actor, ephemeral=True)

    @guild_rules.command(name="poki", description="ma ni la jan poki o toki pona taso")
    @option(
        name="poki",
        description="mi o lukin e jan pi poki ni taso. pana sin la mi lukin e ale.",
    )
    @commands.has_permissions(administrator=True)
    async def guild_toggle_role(self, ctx: ApplicationContext, poki: Role):
        actor = ctx.guild
        assert actor

        result = await DB.toggle_role(actor.id, poki.id)
        if result:
            await ctx.respond(format_role_info(poki.id))
            return
        await ctx.respond(format_removed_role_info(poki.id))

    @guild_rules.command(name="tomo_tenpo", description="tomo seme o pana e sona tenpo")
    @option(name="tomo", description="tomo seme o mun tenpo")
    @commands.has_permissions(administrator=True)
    async def guild_toggle_calendar(
        self, ctx: ApplicationContext, tomo: MessageableGuildChannel
    ):
        actor = ctx.guild
        assert actor

        result = await DB.toggle_calendar(actor.id, tomo.id)
        if result:
            await ctx.respond("kama la mi tenpo e tomo __<#%s>__" % tomo.id)
            return
        await ctx.respond("mi kama lawa ala e tomo __<#%s>__" % tomo.id)

    @guild_rules.command(
        name="lukin", description="ma ni la mi o lukin ala lukin e toki?"
    )
    @commands.has_permissions(administrator=True)
    @option(name="lukin", choices=["lukin", "ala"])
    async def guild_set_disabled(self, ctx: ApplicationContext, lukin: str):
        actor = ctx.guild
        assert actor
        lukin = cast(LukinOptions, lukin)
        return await cmd_set_disabled(ctx, actor, lukin, ephemeral=False)

    @guild_rules.command(
        name="tomo", description="tomo pi ma ni la ale o toki ala toki pona?"
    )
    @option(name="tomo", description="tomo seme, kulupu seme")
    @option(
        name="lukin_ala",
        description="tomo la ilo li lukin ala. ni la ale li ken toki pona ala",
    )
    @commands.has_permissions(administrator=True)
    async def guild_toggle_channel(
        self,
        ctx: ApplicationContext,
        tomo: MessageableGuildChannel | CategoryChannel,
        lukin_ala: bool = False,
    ):
        actor = ctx.guild
        assert actor
        await cmd_upsert_rule(ctx, actor, tomo, lukin_ala, ephemeral=False)

    @guild_rules.command(name="ma", description="ma ni la ale o toki ala toki pona?")
    @commands.has_permissions(administrator=True)
    async def guild_toggle_guild(self, ctx: ApplicationContext):
        ma = ctx.guild
        assert ma  # nasa la ma li ken lawa e ma
        await cmd_upsert_rule(ctx, ma, ma, ephemeral=False)

    @guild_rules.command(
        name="nasin_tenpo",
        description="ilo o lukin kepeken nasin tenpo seme",
    )
    @commands.has_permissions(administrator=True)
    @option(
        name="nasin",
        description="mun la o open lon suno mun lon pimeja mun. wile la o kepeken tenpo wile.",
        choices=["ale", "ala", "mun", "wile"],
    )
    async def guild_set_event_timing(
        self,
        ctx: ApplicationContext,
        nasin: str,
    ):
        ma = ctx.guild
        assert ma
        if nasin == "wile":
            try:
                await DB.get_event_timer(ma.id)
            except InvalidEventTimer as e:
                await ctx.respond(
                    "sina wile kepeken nasin `wile` o pana e tenpo kepeken ilo `/lawa_ma tenpo`"
                )
                return
        await DB.set_timing(ma.id, nasin)
        await ctx.respond("mi kama kepeken nasin __%s__" % nasin)

    @guild_rules.command(
        name="tenpo",
        description="ilo o lukin lon tenpo seme. o kepeken nasin pi ilo Cron",
    )
    @commands.has_permissions(administrator=True)
    @option(
        name="tenpo_lili",
        description="o open lon tenpo lili nanpa seme (pana ala la 0)",
        choices=[str(i) for i in range(0, 60, 30)],
    )
    @option(
        name="tenpo_suli",
        description="o open lon tenpo suli nanpa seme (0-23. ken: 0,12 */6. pana ala la 0.)",
    )
    @option(
        name="tenpo_suno_pi_tenpo_mun",
        description="tenpo mun la o open lon tenpo suno seme (1-31. ken: */7 2,9,13,30. pana ala la *)",
    )
    @option(
        name="tenpo_suno_pi_tenpo_suno_luka_tu",
        description="tenpo suno luka tu la o open lon tenpo suno seme (0-6. mute li ken. pana ala la 6)",
    )
    @option(
        name="tenpo_mun",
        description="o open lon tenpo mun nanpa seme (1-12. mute li ken. ale li ken tan *. pana ala la *)",
    )
    @option(
        name="nasin_tenpo",
        description="tenpo o tan ma seme? (ni li ken UTC li ken CST li ken ante. pana ala la UTC)",
    )
    @option(
        name="suli_tenpo",
        description="tenpo o awen lon tenpo pi suli seme? (ken: 24h, 90m, 3d. pana ala la 24h)",
    )
    async def guild_set_event_time(
        self,
        ctx: ApplicationContext,
        tenpo_lili: str = "0",
        tenpo_suli: str = "0",
        tenpo_suno_pi_tenpo_mun: str = "*",
        tenpo_suno_pi_tenpo_suno_luka_tu: str = "6",
        tenpo_mun: str = "*",
        nasin_tenpo: str = "UTC",
        suli_tenpo: str = "24h",
    ):
        ma = ctx.guild
        assert ma  # nasa la ma li ken lawa e ma

        for t in (
            ale := [
                tenpo_lili,
                tenpo_suli,
                tenpo_suno_pi_tenpo_mun,
                tenpo_mun,
                tenpo_suno_pi_tenpo_suno_luka_tu,
            ]
        ):
            if " " in t:  # TODO: o wawa e pona
                await ctx.respond("ni li ken ala la mi pana ala: `%s`" % t)
                return
        cron = " ".join(ale)

        try:
            timer = EventTimer(cron, nasin_tenpo, suli_tenpo)
        except InvalidEventTimer as e:
            await ctx.respond(
                "%s\n\no lukin e ale: \n`%s` \n`%s` \n`%s`"
                % (e, cron, nasin_tenpo, suli_tenpo)
            )
            return

        prospective_dates = [t for t in timer.get_ranges()]
        formatted = format_date_ranges(prospective_dates)
        if prospective_dates[0][1] > prospective_dates[1][0]:  # TODO
            resp = "pakala li ken la mi pana ala! pini tenpo li lon insa pi open tenpo. o lukin: \n"
            resp += formatted
            await ctx.respond(resp)
            return

        resp = "mi pana la tenpo kama li ni: \n"
        resp += formatted

        await DB.set_cron(ma.id, cron)
        await DB.set_timezone(ma.id, nasin_tenpo)
        await DB.set_length(ma.id, suli_tenpo)

        await ctx.respond(resp)

    """
    User rules. They're nearly identical to guild ones.
    """
    user_rules = SlashCommandGroup(name="lawa")

    @user_rules.command(name="sona", description="ilo ni li ken seme? o pana e sona")
    async def user_help(self, ctx: ApplicationContext):
        await cmd_lawa_help(ctx, ctx.user, ephemeral=True)

    @user_rules.command(name="ale", description="lawa sina li seme?")
    async def user_list_rules(self, ctx: ApplicationContext):
        await cmd_list_rules(ctx, ctx.user, ephemeral=True)

    @user_rules.command(name="weka", description="o weka e lawa ale sina")
    async def user_delete_rules(self, ctx: ApplicationContext):
        await cmd_delete_rules(ctx, ctx.user, ephemeral=True)

    @user_rules.command(name="lukin", description="mi o lukin ala lukin e toki sina?")
    @option(name="lukin", choices=["lukin", "ala"])
    async def user_set_disabled(self, ctx: ApplicationContext, lukin: str):
        lukin = cast(LukinOptions, lukin)  # pycord sucks
        return await cmd_set_disabled(ctx, ctx.user, lukin, ephemeral=True)

    @user_rules.command(
        name="nasin", description="sina toki pona ala la mi o seme e toki?"
    )
    @option(name="nasin", choices=["sitelen", "weka"])
    async def user_set_response(self, ctx: ApplicationContext, nasin: str):
        await DB.set_response(ctx.user.id, nasin)
        await ctx.respond(
            f"sina toki pona ala la mi __{nasin}__ e toki", ephemeral=True
        )

    @user_rules.command(name="tomo", description="tomo la sina o toki ala toki pona?")
    @option(name="tomo", description="tomo seme, kulupu seme")
    @option(
        name="lukin_ala",
        description="tomo la ilo li lukin la. ni la sina ken toki pona ala",
    )
    async def user_toggle_channel(
        self,
        ctx: ApplicationContext,
        tomo: MessageableGuildChannel | CategoryChannel,
        lukin_ala: bool = False,
    ):
        await cmd_upsert_rule(ctx, ctx.user, tomo, lukin_ala, ephemeral=True)

    @user_rules.command(name="ma", description="ma ni la sina o toki ala toki pona?")
    async def user_toggle_guild(
        self,
        ctx: ApplicationContext,
    ):
        ma = ctx.guild
        assert ma
        await cmd_upsert_rule(ctx, ctx.user, ma, ephemeral=True)

    @user_rules.command(
        name="open",
        description="open pi toki sina li ni la mi lukin ala. pana sin la mi lukin.",
    )
    @option(name="toki", description="mi o lukin ala e seme? pana sin la mi lukin.")
    async def user_toggle_opens(self, ctx: ApplicationContext, toki: str):
        opens = await DB.get_opens(ctx.user.id)
        if (len(opens) >= 4) and (toki not in opens):
            await ctx.respond(
                "sina pana pi mute ike. sina wile pana la o weka e toki lon."
            )
            return

        result = await DB.toggle_open(ctx.user.id, toki)
        if result:
            await ctx.respond(
                "open pi toki sina li ni la mi lukin ala: __%s__" % toki, ephemeral=True
            )
            return
        await ctx.respond("mi kama lukin e toki open ni: __%s__" % toki, ephemeral=True)

    @user_rules.command(
        name="sitelen", description="sina toki pona ala la mi pana e sitelen seme"
    )
    @option(
        name="sitelen",
        description="sitelen lili musi en sitelen pi ilo Siko",
    )
    async def user_manage_reacts(self, ctx: ApplicationContext, sitelen: str = ""):
        if not sitelen:
            await DB.set_reacts(ctx.user.id, [])
            _ = await ctx.respond(
                "sina pana ala e sitelen la mi weka e sitelen ale sina", ephemeral=True
            )
            return

        emojis = [e["emoji"] for e in emoji.emoji_list(sitelen)]
        reacts = get_discord_reacts(sitelen)
        if len(emojis) + len(reacts) > 25:
            _ = await ctx.respond(
                "sina pana e sitelen pi mute ike a. o lili e mute", ephemeral=True
            )
            return

        banned_reacts: list[str] = []
        for banned in BANNED_REACTS:
            while banned in emojis:
                emojis.remove(banned)
                banned_reacts.append(banned)
            while banned in reacts:
                reacts.remove(banned)
                banned_reacts.append(banned)

        broken_reacts: list[str] = []
        for react in reacts:
            react_id = re.search(r"\d+", react)
            if not react_id:
                broken_reacts.append(react)
                continue
            react_id = int(react_id.group())

            bot_can_use = self.bot.get_emoji(react_id)
            if not bot_can_use:
                broken_reacts.append(react)

        for react in broken_reacts:
            reacts.remove(react)

        all_reacts = emojis + reacts
        if all_reacts:
            await DB.set_reacts(ctx.user.id, all_reacts)

        resp = format_reacts_management(all_reacts, broken_reacts, banned_reacts)
        _ = await ctx.respond(resp, ephemeral=True)


async def cmd_upsert_rule(
    ctx: ApplicationContext,
    jan_anu_ma: DiscordActor,
    poki: DiscordContainer,
    lukin_ala: bool = False,
    ephemeral: bool = False,
):
    ctype = IjoSiko.CHANNEL
    if isinstance(poki, Guild):
        ctype = IjoSiko.GUILD
    elif isinstance(poki, CategoryChannel):
        ctype = IjoSiko.CATEGORY
    elif isinstance(poki, MessageableGuildChannel):
        ctype = IjoSiko.CHANNEL  # TODO: repetitive
    else:
        LOG.error("Unknown item given to rules: %s", poki)
        LOG.error("... %s" % poki.__dict__)
        await ctx.respond("mi ken ala lawa e ni. ni li seme?")
        return

    action = await DB.upsert_rule(poki.id, ctype, jan_anu_ma.id, lukin_ala)
    response = await build_rule_resp(poki, ctype, action, lukin_ala)
    await ctx.respond(response, ephemeral=ephemeral)


async def cmd_set_disabled(
    ctx: ApplicationContext,
    actor: DiscordActor,
    _disabled: LukinOptions,
    ephemeral: bool,
):
    disabled = False
    if _disabled == "ala":
        disabled = True

    prev_disabled = await DB.get_disabled(actor.id)

    pverb = "kama"
    if prev_disabled == disabled:
        pverb = "awen"

    verb = "lukin"
    if disabled:
        verb = "lukin ala"
    resp = f"mi {pverb} {verb}"

    assert isinstance(disabled, bool)
    await DB.set_disabled(actor.id, disabled)
    await ctx.respond(resp, ephemeral=ephemeral)


async def build_rule_resp(
    container: DiscordContainer,
    ctype: IjoSiko,
    action: Pali,
    exception: bool,
):
    container_ = CONTAINER_MAP[ctype]
    verb = PALI_MAP[action]
    formatted = (
        format_channel(container.id)
        if ctype != IjoSiko.GUILD
        else f"__{container.name}__"  # TODO: formatting guilds in different ways
    )

    result = ""
    if action in (Pali.PANA, Pali.ANTE):
        if exception:
            result += "ona la sina ken toki ale."
        else:
            result += "ona la sina o toki pona taso."

    response = f"{container_} {formatted} la mi {verb} e lawa. {result}"
    return response


# TODO: for following two funcs, better division of user|guild behavior?
async def cmd_list_rules(ctx: ApplicationContext, actor: DiscordActor, ephemeral: bool):
    # TODO: order is controlled by guild/user distinction which is bad.
    guild = ctx.guild
    assert guild
    user = ctx.user
    assert user

    is_guild = isinstance(actor, Guild)

    blurbs = []

    disabled = await DB.get_disabled(actor.id)
    if disabled:
        disabled_info = (
            "**mi lukin ala e toki.** sina wile ante e ni la o kepeken `/lawa lukin`."
        )
        blurbs.append(disabled_info)

    # TODO: sort by guild -> category -> channel considering ownership...
    rules, exceptions = await DB.list_rules(actor.id)
    rules_info = format_rules_exceptions(rules, exceptions)
    blurbs.append(rules_info)

    if not is_guild:
        response = await DB.get_response(actor.id)

        if response == "sitelen":
            reacts = await DB.get_reacts(actor.id)
            reacts_info = format_reacts_rules(reacts)
            blurbs.append(reacts_info)
        else:
            blurbs.append(f"sina toki pona ala la mi {response} e toki sina")

        opens = await DB.get_opens(actor.id)
        if opens:
            opens_info = format_opens_user(opens)
            blurbs.append(opens_info)

    if is_guild:
        role_id = await DB.get_role(actor.id)
        if role_id and (role := guild.get_role(role_id)):
            # safety check in case configured role is deleted
            role_info = format_role_info(role.id)
            blurbs.append(role_info)

        timing = await DB.get_timing(actor.id)
        blurbs.append("nasin tenpo ma li " + format_timing_data(timing))
        if timing == "wile":
            cron = await DB.get_cron(actor.id)
            timezone = await DB.get_timezone(actor.id)
            length = await DB.get_length(actor.id)
            timer = await DB.get_event_timer(actor.id)

            if cron and timezone and length:
                ranges = format_date_ranges([t for t in timer.get_ranges()])
                blurbs.append(format_cron_data(cron, timezone, length) + "\n" + ranges)

    result = "\n\n".join(blurbs)  # TODO: best order?
    await ctx.respond(result, ephemeral=ephemeral)


async def cmd_delete_rules(
    ctx: ApplicationContext, actor: DiscordActor, ephemeral: bool
):
    guild = ctx.guild
    assert guild
    user = ctx.user
    assert user

    await DB.reset_config(actor.id)
    await DB.reset_rules(actor.id)
    await ctx.respond("mi weka e lawa!", ephemeral=ephemeral)


async def cmd_lawa_help(ctx: ApplicationContext, actor: DiscordActor, ephemeral: bool):
    # TODO: order is controlled by guild/user distinction which is bad.
    guild = ctx.guild
    assert guild
    user = ctx.user
    assert user

    is_guild = isinstance(actor, Guild)

    prefix = "/lawa"
    if is_guild:
        prefix = "/lawa_ma"

    sona = "mi __ilo pi toki pona taso__. sina toki pona ala la mi pona e ni. o lukin e ken mi:\n"
    sona += f"- `{prefix} sona`: mi pana e toki ni.\n"
    sona += f"- `{prefix} ale`: mi pana e lawa ale sina.\n"
    sona += f"- `{prefix} lukin [lukin|ala]`: mi lukin ala lukin e toki sina.\n"

    sona += f"- `{prefix} [tomo|ma] (ala)`: mi lukin e ijo. sina pana sin e ijo la mi lukin ala.\n"
    sona += f"  - sina toki pona ala lon ijo la mi pona e ni.\n"
    sona += f"  - `ala` la mi lukin ala e ijo. ijo ni li ken lon insa pi ijo ante.\n"
    sona += f"  - sina wile lawa e ale la o kepeken `/lawa ma`.\n"

    if not is_guild:
        sona += f"- `{prefix} open [toki]`: toki sina li ni lon open la mi lukin ala.\n"
        sona += f"  - sina pana sin e toki la mi weka e ona.\n"
        sona += f"  - open tu wan li ken. mi pana ala e open sin tan mute. o weka e toki lon.\n"

        sona += f"- `{prefix} nasin [sitelen|weka]`: sina toki pona ala la mi seme e toki sina.\n"
        sona += f"- `{prefix} sitelen [sitelen]`: sina toki pona ala la mi pana e sitelen ken seme.\n"
    if is_guild:
        sona += f"- `{prefix} poki [poki]`: mi lukin taso e jan pi poki ni. sina pana sin la mi lukin e jan ale.\n"
        sona += f"- `{prefix} tenpo [ijo mute]`: nasin `cron` la mi lukin e toki lon tenpo. o lukin: <https://crontab.guru/>\n"
        sona += f"  - sina pana ala e `nasin_tenpo` la mi kepeken nasin `UTC`.\n"
        sona += f"  - sina pana ala e `suli_tenpo` la mi kepeken `24h`\n"
        sona += f"  - tenpo suno en ante li ken `*/7`. ni la sina ken kipisi e nanpa tenpo la mi lukin.\n"
        sona += f"  - tenpo suno en ante li ken `2,6,11`. ni la nanpa tenpo li sama ni la mi lukin.\n"

        sona += f"- `{prefix} nasin_tenpo [ale|ala|mun|wile]`: o lukin e toki ma lon nasin tenpo.\n"
        sona += f"  - {format_timing_data('ale')}\n"
        sona += f"  - {format_timing_data('ala')}\n"
        sona += f"  - {format_timing_data('mun')}\n"
        sona += f"  - {format_timing_data('wile')}\n"

    sona += f"\n"
    sona += f"ilo li tan jan Kekan San <@{NANPA_PI_JAN_PALI}>. o kama lon ma ilo: <{NASIN_PI_MA_ILO}>. mu."
    await ctx.respond(sona, ephemeral=ephemeral)
