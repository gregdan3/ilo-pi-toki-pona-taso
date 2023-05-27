# PDM
from discord import (
    User,
    Guild,
    Member,
    TextChannel,
    ForumChannel,
    StageChannel,
    VoiceChannel,
    CategoryChannel,
)

# can't use discord.guild.GuildChannel because it includes categories
MessageableGuildChannel = TextChannel | ForumChannel | StageChannel | VoiceChannel
DiscordContainer = Guild | CategoryChannel | MessageableGuildChannel
DiscordActor = Member | User | Guild
