# STL
import re
from typing import Literal, cast
from datetime import datetime, timedelta

# PDM
import emoji
from discord import Cog, Role, Guild, SlashCommandGroup, option
from discord.ext import commands
from discord.commands.context import ApplicationContext

# LOCAL
from tenpo.types import DiscordActor, MessageableGuildChannel
from tenpo.__main__ import DB
from tenpo.constants import NASIN_PI_MA_ILO, NANPA_PI_JAN_PALI
from tenpo.log_utils import getLogger
from tenpo.str_utils import (
    BANNED_REACTS,
    format_response,
    format_cron_data,
    format_role_info,
    format_opens_user,
    format_date_ranges,
    format_timing_data,
    get_discord_reacts,
    discord_fmt_datetime,
    format_rules_exceptions,
    format_reacts_management,
    format_removed_role_info,
)
from tenpo.rules_menu import EnterRule
from tenpo.croniter_utils import (
    InvalidTZ,
    EventTimer,
    InvalidDelta,
    InvalidEventTimer,
    parse_delta,
    parse_timezone,
    parse_delta_safe,
)

LOG = getLogger()

LukinOptions = Literal["lukin", "ala"]
SpoilerOptions = Literal["ken", "ala"]

MAX_SLEEP = timedelta(days=1)


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

    @guild_rules.command(name="seme", description="ma ni la lawa li seme?")
    async def guild_list_rules(self, ctx: ApplicationContext):
        actor = ctx.guild
        assert actor
        await cmd_list_rules(ctx, actor, ephemeral=True)

    @guild_rules.command(name="weka", description="o weka e lawa ale ma")
    @commands.has_guild_permissions(manage_channels=True)
    async def guild_delete_rules(self, ctx: ApplicationContext):
        actor = ctx.guild
        assert actor
        await cmd_delete_all_rules(ctx, actor, ephemeral=True)

    @guild_rules.command(name="poki", description="ma ni la jan poki o toki pona taso")
    @option(
        name="poki",
        description="mi o lukin e jan pi poki ni taso. pana sin la mi lukin e ale.",
    )
    @commands.has_guild_permissions(manage_channels=True)
    async def guild_toggle_role(self, ctx: ApplicationContext, poki: Role):
        actor = ctx.guild
        assert actor

        result = await DB.toggle_role(actor.id, poki.id)
        if result:
            await ctx.respond(format_role_info(poki.id), ephemeral=True)
            return
        await ctx.respond(format_removed_role_info(poki.id), ephemeral=True)

    @guild_rules.command(name="tomo_tenpo", description="tomo seme o pana e sona tenpo")
    @option(name="tomo", description="tomo seme o mun tenpo")
    @commands.has_guild_permissions(manage_channels=True)
    async def guild_toggle_calendar(
        self, ctx: ApplicationContext, tomo: MessageableGuildChannel
    ):
        actor = ctx.guild
        assert actor

        result = await DB.toggle_calendar(actor.id, tomo.id)
        if result:
            await ctx.respond(
                "mi kama tenpo e tomo __<#%s>__" % tomo.id, ephemeral=True
            )
            return
        await ctx.respond(
            "mi kama tenpo ala e tomo __<#%s>__" % tomo.id, ephemeral=True
        )

    @guild_rules.command(
        name="len", description="ma ni la jan o ken ala ken len e toki?"
    )
    @commands.has_guild_permissions(manage_channels=True)
    @option(name="len", choices=["ken", "ala"])
    async def guild_set_spoilers(self, ctx: ApplicationContext, len: str):
        actor = ctx.guild
        assert actor
        len = cast(SpoilerOptions, len)  # pycord sucks
        return await cmd_set_spoilers(ctx, actor, len, ephemeral=True)

    @guild_rules.command(
        name="lukin", description="ma ni la mi o lukin ala lukin e toki?"
    )
    @commands.has_guild_permissions(manage_channels=True)
    @option(name="lukin", choices=["lukin", "ala"])
    async def guild_set_disabled(self, ctx: ApplicationContext, lukin: str):
        actor = ctx.guild
        assert actor
        lukin = cast(LukinOptions, lukin)
        return await cmd_set_disabled(ctx, actor, lukin, ephemeral=True)

    @guild_rules.command(
        name="lape", description="mi o lukin ala e toki ma lon tenpo pi suli seme?"
    )
    @commands.has_guild_permissions(manage_channels=True)
    @option(
        name="tenpo",
        description="tenpo o suli seme? (ken: 24h, 90m, 3d, 0m. 0m la mi weka e lape.)",
    )
    async def guild_set_sleep(self, ctx: ApplicationContext, tenpo: str):
        actor = ctx.guild
        assert actor
        return await cmd_set_sleep(ctx, actor, tenpo, ephemeral=True)

    @guild_rules.command(name="sin", description="o toki pona taso e seme?")
    @commands.has_guild_permissions(manage_channels=True)
    async def guild_create_rule(self, ctx: ApplicationContext):
        actor = ctx.guild
        assert actor
        await ctx.respond(
            "sina wile lawa e seme lon ma?",
            view=EnterRule(ctx.guild),
            ephemeral=True,
        )

    @guild_rules.command(
        name="nasin_tenpo",
        description="ilo o lukin kepeken nasin tenpo seme",
    )
    @commands.has_guild_permissions(manage_channels=True)
    @option(
        name="nasin",
        description="mun la o open lon suno mun lon pimeja mun. wile la o kepeken tenpo wile.",
        choices=["ale", "ala", "mun", "wile"],
    )
    async def guild_set_event_timing_method(
        self,
        ctx: ApplicationContext,
        nasin: str,
    ):
        ma = ctx.guild
        assert ma
        await DB.set_timing(ma.id, nasin)
        await ctx.respond("mi kama kepeken nasin __%s__" % nasin)

    @guild_rules.command(
        name="tenpo",
        description="nasin Cron la ilo o lukin lon tenpo seme? (https://crontab.guru/)",
    )
    @commands.has_guild_permissions(manage_channels=True)
    @option(
        name="tenpo_lili",
        description="tenpo lili nanpa seme? (pana ala la 0)",
        choices=[str(i) for i in range(0, 60, 15)],
    )
    @option(
        name="tenpo_suli",
        description="tenpo suli nanpa seme? (0-23. ken: 0,12 */6. pana ala la 0.)",
    )
    @option(
        name="tenpo_suno_pi_tenpo_mun",
        description="tenpo mun la tenpo suno seme? (1-31. ken: */7 2,9,13,30. pana ala la *)",
    )
    @option(
        name="tenpo_suno_pi_tenpo_esun",
        description="tenpo esun la tenpo suno seme? (0-6. ken: */2 2,6. pana ala la 6)",
    )
    @option(
        name="tenpo_mun",
        description="tenpo mun nanpa seme? (1-12. ken: * */3 1,4,9,11. pana ala la *)",
    )
    @option(
        name="nasin_tenpo_ma",
        description="nasin tenpo ma seme? (ken: CST, UTC-6, US/Central. pana ala la UTC)",
    )
    @option(
        # TODO: make optional. fetch current if missing
        name="suli_tenpo",
        description="tenpo o suli seme? (ken: 24h, 90m, 3d, 1mo. pana ala la 24h)",
    )
    async def guild_set_event_time_full(
        self,
        ctx: ApplicationContext,
        tenpo_lili: str = "0",
        tenpo_suli: str = "0",
        tenpo_suno_pi_tenpo_mun: str = "*",
        tenpo_suno_pi_tenpo_suno_luka_tu: str = "6",
        tenpo_mun: str = "*",
        nasin_tenpo_ma: str = "UTC",
        suli_tenpo: str = "24h",
    ):
        ma = ctx.guild
        assert ma

        ale = [
            tenpo_lili,
            tenpo_suli,
            tenpo_suno_pi_tenpo_mun,
            tenpo_mun,
            tenpo_suno_pi_tenpo_suno_luka_tu,
        ]
        cron = " ".join(ale)

        try:
            timer = EventTimer(cron, nasin_tenpo_ma, suli_tenpo)
        except InvalidEventTimer as e:
            await ctx.respond(
                "%s\no lukin e ale: \n`%s` \n`%s` \n`%s`\n\nsina wile e sona pi ilo Cron la o lukin e ni: <https://crontab.guru/>"
                % (e, cron, nasin_tenpo_ma, suli_tenpo),
                ephemeral=True,
            )
            return

        prospective_dates = [t for t in timer.get_events_from()]
        formatted = format_date_ranges(prospective_dates)
        if prospective_dates[0][1] > prospective_dates[1][0]:  # TODO: this sucks
            resp = "pakala li ken la mi pana ala! pini tenpo li lon insa pi open tenpo. o lukin: \n"
            resp += formatted
            await ctx.respond(resp, ephemeral=True)
            return

        resp = "mi pana la tenpo kama li ni: \n"
        resp += formatted

        await DB.set_cron(ma.id, cron)
        await DB.set_timezone(ma.id, nasin_tenpo_ma)
        await DB.set_length(ma.id, suli_tenpo)

        await ctx.respond(resp, ephemeral=True)

    @guild_rules.command(
        name="suli_tenpo",
        description="tenpo pi toki pona taso o suli seme?",
    )
    @commands.has_guild_permissions(manage_channels=True)
    @option(
        name="suli_tenpo",
        description="tenpo o suli seme? (ken: 24h, 90m, 3d, 1mo)",
    )
    async def guild_set_event_length(
        self,
        ctx: ApplicationContext,
        suli_tenpo: str,
    ):
        ma = ctx.guild
        assert ma

        try:
            delta = parse_delta(suli_tenpo, must_be_positive=True)
        except InvalidDelta as e:
            await ctx.respond(e, ephemeral=True)
            return

        await DB.set_length(ma.id, suli_tenpo)
        resp = f"tenpo kama pi toki pona taso li suli ni: {suli_tenpo}"

        await ctx.respond(resp, ephemeral=True)

    @guild_rules.command(
        name="nasin_tenpo_ma",
        description="mi o kepeken nasin tenpo pi ma seme?",
    )
    @commands.has_guild_permissions(manage_channels=True)
    @option(
        name="nasin_tenpo_ma",
        description="nasin tenpo ma seme? (ken: CST, UTC-6, US/Central)",
    )
    async def guild_set_timezone(
        self,
        ctx: ApplicationContext,
        nasin_tenpo_ma: str,
    ):
        ma = ctx.guild
        assert ma

        try:
            parse_timezone(nasin_tenpo_ma)
        except InvalidTZ as e:
            await ctx.respond(e)
            return

        await DB.set_timezone(ma.id, nasin_tenpo_ma)
        resp = f"mi kama kepeken nasin tenpo ma ni: {nasin_tenpo_ma}"
        await ctx.respond(resp)

    """
    User rules. They're nearly identical to guild ones.
    """
    user_rules = SlashCommandGroup(name="lawa")

    @user_rules.command(name="sona", description="ilo ni li ken seme? o pana e sona")
    async def user_help(self, ctx: ApplicationContext):
        await cmd_lawa_help(ctx, ctx.user, ephemeral=True)

    @user_rules.command(name="seme", description="lawa sina li seme?")
    async def user_list_rules(self, ctx: ApplicationContext):
        await cmd_list_rules(ctx, ctx.user, ephemeral=True)

    @user_rules.command(name="weka", description="o weka e lawa ale sina")
    async def user_delete_rules(self, ctx: ApplicationContext):
        await cmd_delete_all_rules(ctx, ctx.user, ephemeral=True)

    @user_rules.command(name="len", description="sina o ken ala ken len e toki?")
    @option(name="len", choices=["ken", "ala"])
    async def user_set_spoilers(self, ctx: ApplicationContext, len: str):
        len = cast(SpoilerOptions, len)  # pycord sucks
        return await cmd_set_spoilers(ctx, ctx.user, len, ephemeral=True)

    @user_rules.command(name="lukin", description="mi o lukin ala lukin e toki sina?")
    @option(name="lukin", choices=["lukin", "ala"])
    async def user_set_disabled(self, ctx: ApplicationContext, lukin: str):
        lukin = cast(LukinOptions, lukin)  # pycord sucks
        return await cmd_set_disabled(ctx, ctx.user, lukin, ephemeral=True)

    @user_rules.command(
        name="lape", description="mi o lukin ala e toki sina lon tenpo pi suli seme?"
    )
    @option(
        name="tenpo",
        description="tenpo o suli seme? (ken: 24h, 90m, 3d, 0m. 0m la mi weka e lape.)",
    )
    async def user_set_sleep(self, ctx: ApplicationContext, tenpo: str):
        return await cmd_set_sleep(ctx, ctx.user, tenpo, ephemeral=True)

    @user_rules.command(
        name="nasin", description="sina toki pona ala la mi o seme e toki?"
    )
    @option(name="nasin", choices=["sitelen", "weka", "len", "sitelen lili"])
    async def user_set_response(self, ctx: ApplicationContext, nasin: str):
        await DB.set_response(ctx.user.id, nasin)
        await ctx.respond(
            f"sina toki pona ala la mi __{nasin}__ e toki", ephemeral=True
        )

    @user_rules.command(name="sin", description="o toki pona taso e seme?")
    async def user_create_rule(self, ctx: ApplicationContext):
        await ctx.respond(
            "sina wile lawa e seme?",
            view=EnterRule(ctx.user),
            ephemeral=True,
        )

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


async def cmd_set_spoilers(
    ctx: ApplicationContext,
    actor: DiscordActor,
    _allowed: SpoilerOptions,
    ephemeral: bool,
):
    allowed = False
    if _allowed == "ken":
        allowed = True

    prev_allowed = await DB.get_spoilers(actor.id)

    pverb = "kama"
    if prev_allowed == allowed:
        pverb = "awen"

    verb = "ken"
    if not allowed:
        verb = "ken ala"
    resp = f"len li {pverb} {verb}"

    assert isinstance(allowed, bool)
    await DB.set_spoilers(actor.id, allowed)
    await ctx.respond(resp, ephemeral=ephemeral)


async def cmd_set_sleep(
    ctx: ApplicationContext,
    actor: DiscordActor,
    tenpo: str,
    ephemeral: bool,
):
    delta = parse_delta_safe(tenpo)
    if delta is None:
        await ctx.respond(f"sitelen tenpo ni li pakala: {tenpo}", ephemeral=ephemeral)
        return

    if delta.total_seconds() < 30:
        await DB.set_sleep_int(actor.id, 0)
        await ctx.respond(f"mi kama lape ala li lukin e toki", ephemeral=ephemeral)
        return

    if delta > MAX_SLEEP:
        await ctx.respond(
            f"tenpo lape `{tenpo}` li suli ike. ken la o kepeken `/lawa lukin`",
            ephemeral=ephemeral,
        )
        return

    sleep_to = datetime.now() + delta
    await DB.set_sleep(actor.id, sleep_to)
    await ctx.respond(
        f"mi lape li kama lukin sin e toki lon tenpo ni: {discord_fmt_datetime(sleep_to)}",
        ephemeral=ephemeral,
    )


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
    if not rules_info:
        rules_info = "**lawa lukin li lon ala** la mi lukin ala e toki sina.\no pana e lawa kepeken `/lawa sin`"

    blurbs.append(rules_info)

    if not is_guild:
        response = await DB.get_response(actor.id)

        if response.startswith("sitelen"):
            reacts = await DB.get_reacts(actor.id)
            reacts_info = format_response(response, reacts)
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

        method = await DB.get_timing(actor.id)
        cron = await DB.get_cron(actor.id)
        timezone = await DB.get_timezone(actor.id)
        length = await DB.get_length(actor.id)
        if cron and timezone and length and method == "wile":
            try:
                timer = await DB.get_event_timer(actor.id)
                ranges = format_date_ranges([t for t in timer.get_events_from()])
                blurbs.append(format_cron_data(cron, timezone, length) + "\n" + ranges)
            except InvalidEventTimer as e:
                blurbs.append(format_cron_data(cron, timezone, length))
                blurbs.append(str(e))

        if timezone and length and method == "mun":
            try:
                timer = await DB.get_moon_timer(actor.id)
                ranges = format_date_ranges([t for t in timer.get_events_from()])
                blurbs.append(format_cron_data("mun", timezone, length) + "\n" + ranges)
            except InvalidEventTimer as e:
                blurbs.append(format_cron_data("mun", timezone, length))
                blurbs.append(str(e))

    result = "\n\n".join(blurbs)  # TODO: best order?
    await ctx.respond(result, ephemeral=ephemeral)


async def cmd_delete_all_rules(
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
    is_guild = isinstance(actor, Guild)

    prefix = "/lawa"
    ref = "sina"
    if is_guild:
        prefix = "/lawa_ma"
        ref = "ma"

    # NOTE: double check the placement of substitution strings!
    sona = f"""
## sona ilo
mi __ilo pi toki pona taso__ li pona e toki {ref}! o lukin e ken mi:
### sona
- `{prefix} sona`: mi pana e toki ni.
- `{prefix} ale`: mi pana e sona ni: ilo li seme e sina lon seme?
### ken
- `{prefix} lukin [lukin|ala]`: mi lukin ala lukin e toki {ref}.
- `{prefix} len [ken|ala]`: toki {ref} li ken ala ken kepeken nasin len ||ni||.%(ken)s
### lawa lukin
- `{prefix} [sin]`: mi o lukin e toki lon seme? 
  - toki li pona ala lon ijo la mi pona e ni.
  - sina pana sin e lawa sama la mi weka e ona.
  - sina ken ken e toki ale lon tomo, lon insa pi tomo pi toki pona taso.%(lawa_tenpo)s

-# ilo li tan mun Kekan San <@{NANPA_PI_JAN_PALI}>. o kama lon ma ilo: <{NASIN_PI_MA_ILO}>. mu.
"""

    ken_jan = f"""
- `{prefix} nasin [sitelen|weka]`: toki {ref} li pona ala la mi seme e toki?
- `{prefix} sitelen [sitelen]`: toki {ref} li pona ala la mi pana e sitelen seme?
  - sitelen ma <:tokipona:448287759266742272> en sitelen ilo 💥 li ken.
  - sina pana e sitelen sama lon tenpo mute la sina suli e ken sitelen.
  - sina pana e ala la mi weka e sitelen ale sina.
- `{prefix} open [toki]`: open toki li ni la mi lukin ala.
  - open tu wan li ken. sina wile e ona sin la o weka e ona lon.
  - sina pana sin e open la mi lukin e ona lon tenpo kama."""

    ken_ma = f"""
- `{prefix} poki [poki]`: mi lukin taso e jan pi poki ni. sina pana sin la mi lukin e jan ale."""

    lawa_tenpo = f"""
### lawa tenpo
- `{prefix} nasin_tenpo [ale|ala|mun|wile]`: o lukin e toki ma lon nasin tenpo.
  - {format_timing_data('ale')}
  - {format_timing_data('ala')}
  - {format_timing_data('mun')}
  - {format_timing_data('wile')}
- `{prefix} tenpo [ijo mute]`: nasin Cron la mi lukin e toki {ref} lon tenpo. <https://crontab.guru/>
  - sina pana ala e `nasin_tenpo` la mi kepeken nasin tenpo `UTC`.
  - sina pana ala e `suli_tenpo` la mi kepeken suli tenpo `24h`
- `{prefix} suli_tenpo [suli_tenpo]`: tenpo pi toki pona taso o suli seme?
- `{prefix} nasin_tenpo_ma [nasin_tenpo_ma]`: mi kepeken nasin tenpo pi ma seme?"""

    subs = {}
    if is_guild:
        subs["ken"] = ken_ma
        subs["lawa_tenpo"] = lawa_tenpo
    else:
        subs["ken"] = ken_jan
        subs["lawa_tenpo"] = ""
    sona = sona % subs

    await ctx.respond(sona, ephemeral=ephemeral)
