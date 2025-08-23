# STL
from typing import TypedDict, cast

# PDM
from discord import (
    Guild,
    Thread,
    ButtonStyle,
    ChannelType,
    Interaction,
    SelectOption,
    ComponentType,
    CategoryChannel,
    ui,
)
from discord.ui import View, Button, Select

# LOCAL
from tenpo.db import Pali, IjoSiko
from tenpo.types import (
    DiscordUser,
    DiscordActor,
    GuildContainer,
    DiscordContainer,
    MessageableGuildChannel,
)
from tenpo.__main__ import DB
from tenpo.log_utils import getLogger
from tenpo.str_utils import get_noun, get_verb

LOG = getLogger()


class RuleData(TypedDict):
    actor: DiscordActor
    container: DiscordContainer | DiscordActor | None
    label: str  # name or mention
    exception: bool
    action: Pali


def get_ctype(item: DiscordContainer | DiscordActor) -> IjoSiko:
    if isinstance(item, Guild):
        return IjoSiko.GUILD
    if isinstance(item, CategoryChannel):
        return IjoSiko.CATEGORY
    if isinstance(item, MessageableGuildChannel):
        return IjoSiko.CHANNEL
    if isinstance(item, Thread):
        return IjoSiko.THREAD
    if isinstance(item, DiscordUser):
        return IjoSiko.ALL
    return IjoSiko.NONE


class BaseView(View):
    def __init__(self, actor: DiscordActor, *, timeout: int = 120):
        super().__init__(timeout=timeout)
        self.actor = actor
        self.add_item(self.CancelButton(self.actor))
        self.add_item(self.RestartButton(self.actor))

    class CancelButton(Button):
        def __init__(self, actor: DiscordActor):
            super().__init__(label="o pini", style=ButtonStyle.danger, row=4)
            self.actor = actor

        async def callback(self, interaction: Interaction):
            await interaction.response.edit_message(
                content="pini! o sona e lawa sina kepeken `/lawa seme`",
                view=None,
            )

    class RestartButton(Button):
        def __init__(self, actor: DiscordActor):
            super().__init__(label="o sin", style=ButtonStyle.secondary, row=4)
            self.actor = actor

        async def callback(self, interaction: Interaction):
            await interaction.response.edit_message(
                content="sina open sin. sina wile lawa e seme?",
                view=EnterRule(self.actor),
            )


class EnterRule(BaseView):
    def __init__(self, actor: DiscordActor):
        super().__init__(actor)
        options = [
            SelectOption(label="ale", description="o lawa e ale"),
            SelectOption(label="ma", description="o lawa e ma pi ilo Siko"),
            SelectOption(label="tomo", description="o lawa e tomo lon ma ni"),
        ]
        if isinstance(actor, Guild):  # guilds cannot assign ale
            options = options[:2]
        # TODO: if this is a DM, remove/disable tomo?

        self.add_item(self.SelectRuleType(actor, options))

    class SelectRuleType(Select):
        def __init__(self, actor: DiscordActor, options: list[SelectOption]):
            super().__init__(placeholder="ijo", options=options)
            self.actor = actor

        async def callback(self, interaction: Interaction):
            choice = cast(str, self.values[0])
            rule = RuleData(
                actor=self.actor,
                container=self.actor,  # user is their own container
                exception=False,
                label="ale",
                action=Pali.PANA,
            )

            if choice == "ale":
                await confirm_helper(self.actor, rule, False, interaction)
                return

            elif choice == "ma":
                if isinstance(self.actor, Guild):
                    rule.update(label=self.actor.name)
                    await confirm_helper(self.actor, rule, False, interaction)
                    return

                # user makes rule for guild
                await interaction.response.edit_message(
                    content=f"sina wile lawa e {choice} seme?",
                    view=SelectGuild(self.actor),
                )

            elif choice == "tomo":
                await interaction.response.edit_message(
                    content=f"sina wile lawa e {choice} seme?",
                    view=SelectChannel(self.actor),
                )


class SelectGuild(BaseView):
    def __init__(self, actor: DiscordUser):
        super().__init__(actor)
        if isinstance(actor, Guild):
            guilds = [actor]
        else:
            guilds = actor.mutual_guilds

        options = [SelectOption(label=g.name, value=str(g.id)) for g in guilds]
        self.add_item(_GuildPicker(actor, options))


class _GuildPicker(Select):
    def __init__(self, actor: DiscordUser, options: list[SelectOption]):
        super().__init__(
            placeholder="ma pi ilo Siko",
            min_values=1,
            max_values=1,
            options=options,
        )
        self.actor = actor

    async def callback(self, interaction: Interaction):
        guild_id = int(cast(str, self.values[0]))
        guild = interaction.client.get_guild(guild_id)
        if not guild:
            await interaction.response.edit_message(
                content="⚠️ mi ken ala sona e ma ni. ken la pakala li lon. o sin.",
                view=EnterRule(self.actor),
            )
            return

        rule = RuleData(
            actor=self.actor,
            container=guild,
            exception=False,
            label=guild.name,
            action=Pali.PANA,
        )
        await confirm_helper(self.actor, rule, True, interaction)


class SelectChannel(BaseView):
    def __init__(self, actor: DiscordActor):
        super().__init__(actor)
        allowed = [
            ChannelType.category,
            ChannelType.text,
            ChannelType.voice,
            ChannelType.news,
            ChannelType.stage_voice,
            ChannelType.forum,
            ChannelType.public_thread,
            ChannelType.private_thread,
        ]
        self.add_item(_ChannelPicker(self.actor, allowed))


class _ChannelPicker(Select):
    def __init__(self, actor: DiscordActor, allowed: list[ChannelType]):
        super().__init__(
            select_type=ComponentType.channel_select,
            channel_types=allowed,
            placeholder="tomo pi ma ni",
            min_values=1,
            max_values=1,
        )
        # TODO: list only channels the user can message
        #       or categories containing such channels
        self.actor = actor

    async def callback(self, interaction: Interaction):
        channel = cast(GuildContainer, self.values[0])
        rule = RuleData(
            actor=self.actor,
            container=channel,
            exception=False,
            label=channel.mention,
            action=Pali.PANA,
        )
        await confirm_helper(self.actor, rule, True, interaction)


class ExceptionConfirm(BaseView):
    def __init__(self, actor: DiscordActor, rule: RuleData):
        super().__init__(actor)
        self.rule = rule

    @ui.button(label="o toki pona taso", style=ButtonStyle.primary)
    async def make_tpt(self, _, interaction: Interaction):
        self.rule.update(exception=False)
        await confirm_helper(self.actor, self.rule, False, interaction)

    @ui.button(label="o ken toki ale", style=ButtonStyle.secondary)
    async def allow_all(self, _, interaction: Interaction):
        self.rule.update(exception=True)
        await confirm_helper(self.actor, self.rule, False, interaction)


class ActionConfirm(BaseView):
    def __init__(self, actor: DiscordActor, rule: RuleData):
        super().__init__(actor)
        self.rule = rule

    @ui.button(label="wile", style=ButtonStyle.success)
    async def confirm(self, _, interaction: Interaction):
        await upsert_rule(self.actor, self.rule)
        verb = get_verb(self.rule["action"])
        await interaction.response.edit_message(
            content=f"mi {verb} e ona!",
            view=BaseView(self.actor),
        )

    @ui.button(label="ala", style=ButtonStyle.secondary)
    async def cancel(self, _, interaction: Interaction):
        # await upsert_rule(self.actor, self.rule)
        verb = get_verb(self.rule["action"])
        await interaction.response.edit_message(
            content=f"mi ante ala e lawa! sina wile lawa e seme ante?",
            view=BaseView(self.actor),
        )


async def confirm_helper(
    actor: DiscordActor,
    rule: RuleData,
    check_exception: bool,
    interaction: Interaction,
):
    label = rule["label"]
    noun = get_noun(rule["container"])
    verb = get_verb(rule["action"])
    note = "**toki pona taso**"
    if rule["exception"]:
        note = "ken e **toki ale**"

    eid = actor.id
    id = rule["container"].id
    ctype = get_ctype(rule["container"])
    exists, exception = await DB.select_rule(id, ctype, eid)
    # TODO: what if `exception` is different?

    if not exists and not check_exception:
        await interaction.response.edit_message(
            content=f"sina wile ala wile {note} lon {noun} **{label}**?",
            view=ActionConfirm(actor, rule),
        )
        return

    if not exists and check_exception:
        await interaction.response.edit_message(
            content=f"sina pana e {noun} **{label}**. ona o seme?",
            view=ExceptionConfirm(actor, rule),
        )
        return

    rule.update(action=Pali.WEKA)
    verb = get_verb(rule["action"])
    await interaction.response.edit_message(
        content=f"⚠️ lawa li lon {noun} **{label}** lon tenpo ni. sina wile ala wile {verb} e ona?",
        view=ActionConfirm(actor, rule),
    )


async def upsert_rule(actor: DiscordActor, rule: RuleData):
    eid = actor.id
    id = rule["container"].id
    ctype = get_ctype(rule["container"])
    exception = rule["exception"]
    result = await DB.upsert_rule(id, ctype, eid, exception)
    return result
