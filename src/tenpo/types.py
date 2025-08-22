# PDM
from discord import (
    User,
    Guild,
    Member,
    Thread,
    TextChannel,
    ForumChannel,
    StageChannel,
    VoiceChannel,
    CategoryChannel,
)

# can't use discord.guild.GuildChannel because it includes categories
MessageableGuildChannel = TextChannel | ForumChannel | StageChannel | VoiceChannel
GuildContainer = MessageableGuildChannel | CategoryChannel | Thread
DiscordContainer = Guild | GuildContainer

DiscordUser = Member | User
DiscordActor = DiscordUser | Guild
