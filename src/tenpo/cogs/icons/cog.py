# STL
import logging
from io import BytesIO
from typing import Tuple, Optional
from datetime import datetime

# PDM
from discord import File, User, SlashCommandGroup, AutocompleteContext
from __main__ import TenpoBot
from discord.ext import commands
from discord.channel import TextChannel
from discord.commands import option
from discord.ext.commands import Cog
from discord.commands.context import ApplicationContext

# LOCAL
from tenpo.__main__ import DB  # fat sigh
from tenpo.image_utils import ImageDict, make_filename, download_image
from tenpo.autocomplete_utils import autocomplete_filter

LOG = logging.getLogger("tenpo")
LOG.warning("This module is not ready for production!")


def prep_for_embed(image: ImageDict) -> File:
    return File(BytesIO(image["bytes"]), filename=make_filename(image))


async def icon_autocomplete(ctx: AutocompleteContext):
    guild_id = ctx.interaction.guild_id
    return autocomplete_filter(ctx.value, DB.get_icon_banner_names(guild_id))


class CogIcons(Cog):
    def __init__(self, bot):
        self.bot: TenpoBot = bot

    icon = SlashCommandGroup(
        name="icon", description="Set, upload, and delete server icons and banners"
    )

    @icon.command(name="default", description="Set default icon and banner")
    @option(
        "name",
        description="The name of your icon/banner",
        autocomplete=icon_autocomplete,
    )
    async def set_default_icon(self, ctx: ApplicationContext, name: str):
        guild = ctx.guild
        channel = ctx.channel
        assert guild
        if not isinstance(channel, TextChannel):
            return
        await DB.set_default_icon_banner(guild.id, name)
        icon_banner_row = await DB.get_icon_banner_by_name(guild.id, name)

    @icon.command(name="get", description="Get an icon/banner by name.")
    @commands.has_permissions(administrator=True)
    @option(
        "name",
        description="Name of icon/banner to get.",
        autocomplete=icon_autocomplete,
    )
    async def get_icon(
        self, ctx: ApplicationContext, name: str
    ):  # TODO: autocomplete from db
        guild = ctx.guild
        assert guild
        icon_banner = DB.get_icon_banner_by_name(guild.id, name=name)
        if not icon_banner:
            await ctx.respond("No such icon or banner!")
        # TODO: show user the banners lmao

        await ctx.respond("Not implemented!", ephemeral=True)

    @icon.command(name="delete")
    @commands.has_permissions(administrator=True)
    async def delete_icon(self, ctx: ApplicationContext):
        pass

    @icon.command(name="update")
    @commands.has_permissions(administrator=True)
    @option("name", description="Name your icon (and banner)!")
    @option("author", description="Creator of icon/banner", default=None, type=User)
    @option("event", description="Config for the ", default="")
    async def update_icon_banner(self, ctx: ApplicationContext):
        pass

    @icon.command(name="upload")
    @commands.has_permissions(administrator=True)
    @option("name", description="Name your icon (and banner)!")
    @option("icon_url", description="URL to your icon")
    @option("banner_url", description="URL to your banner", default=None)
    @option("author", description="Creator of icon/banner", default=None, type=User)
    @option("event", description="The event this icon/banner is for", default="")
    async def upload_icon_banner(
        self,
        ctx: ApplicationContext,
        name: str,
        icon_url: str,
        banner_url: str = "",
        author: Optional[User] = None,
        event: str = "",
        default: bool = False,
    ):
        await ctx.defer()
        resp = await _upload_icon_banner(
            self.bot,
            ctx=ctx,
            name=name,
            icon_url=icon_url,
            banner_url=banner_url,
            author=author,
            event=event,
            default=default,
        )
        if resp:  # TODO: invert, appease pyright
            icon, banner = resp
            await ctx.send(file=prep_for_embed(icon))
            if banner:
                await ctx.send(file=prep_for_embed(banner))
            await ctx.respond("Successfully uploaded these!", ephemeral=True)
            return
        await ctx.respond(
            "Couldn't complete the request! Is the icon or banner valid?",
            ephemeral=True,
        )


async def _upload_icon_banner(
    bot: TenpoBot,
    ctx: ApplicationContext,
    name: str,
    icon_url: str,
    banner_url: Optional[str],
    author: Optional[User],
    event: Optional[str],
    default: bool = False,
) -> Optional[Tuple[ImageDict, Optional[ImageDict]]]:
    guild = ctx.guild
    channel = ctx.channel
    assert guild
    if not isinstance(channel, TextChannel):
        return

    icon = await download_image(icon_url) if icon_url else None
    banner = await download_image(banner_url) if banner_url else None
    config = {"event": f"{event}"} if event else None

    if not icon:
        return

    id = await DB.insert_icon_banner(
        guild_id=guild.id,
        author_id=author.id if author else None,  # TODO
        name=name,
        last_used=datetime.now(),
        config=config,
        icon=icon["bytes"],
        banner=banner["bytes"] if banner and banner["bytes"] else None,
    )
    if default:
        await DB.update_guild_default_icon_banner(
            guild_id=guild.id, default_icon_banner_id=id
        )

    return icon, banner
