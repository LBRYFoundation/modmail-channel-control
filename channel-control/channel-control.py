import discord
from discord.ext import commands

from core import checks
from core.checks import PermissionLevel
from core.models import DMDisabled


class ChannelControl(commands.Cog):
    """Controls channels and enables/disables new thread creaation based on the number of channels"""
    def __init__(self, bot):
        self.bot = bot
        self.total_allowed_channels = 500
        self.db = self.bot.plugin_db.get_partition(self)

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        if channel.guild != self.bot.modmail_guild:
            return

        current_channels = len(self.bot.modmail_guild.channels)
        config = await self.db.find_one({'_id': 'config'}) or {}
        max_channel_limit = config.get('max_channel_limit') or 100
        if current_channels / self.total_allowed_channels * 100 > max_channel_limit and self.bot.config["dm_disabled"] < DMDisabled.NEW_THREADS:
            # disable threads
            self.bot.config["dm_disabled"] = DMDisabled.NEW_THREADS

            if config.get('disabled_full_response'):
                self.bot.config["disabled_current_thread_response"] = config['disabled_full_response']

            await self.bot.config.update()
            em = discord.Embed(
                title='Channel Control: New threads disabled',
                description=f'Total Channel Count ({current_channels}) > Min limit ({max_channel_limit}%)',
                color=self.bot.error_color
            )
            await self.bot.log_channel.send(embed=em)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        if channel.guild != self.bot.modmail_guild:
            return

        current_channels = len(self.bot.modmail_guild.channels)
        config = await self.db.find_one({'_id': 'config'}) or {}
        min_channel_limit = config.get('min_channel_limit') or 0
        if current_channels / self.total_allowed_channels * 100 < min_channel_limit and self.bot.config["dm_disabled"] >= DMDisabled.NEW_THREADS:
            # disable threads
            self.bot.config["dm_disabled"] = DMDisabled.NONE

            if config.get('disabled_default_response'):
                self.bot.config["disabled_current_thread_response"] = config['disabled_default_response']

            await self.bot.config.update()

            em = discord.Embed(
                title='Channel Control: New threads enabled',
                description=f'Total Channel Count ({current_channels}) < Min limit ({min_channel_limit}%)',
                color=self.bot.main_color
            )
            await self.bot.log_channel.send(embed=em)

    @checks.has_permissions(PermissionLevel.MODERATOR)
    @commands.command()
    async def ccconfig(self, ctx, key: str, value: str=""):
        """Valid keys: max_channel_limit, min_channel_limit, disabled_full_response, disabled_default_response
        All limits should be 0-100 (percent)

        Leave value blank to reset
        """
        if value.isdigit():
            value = int(value)
        if key in ('max_channel_limit', 'min_channel_limit', 'disabled_full_response, disabled_default_response'):
            await self.db.find_one_and_update({'_id': 'config'}, {'$set': {key: value}}, upsert=True)
            await ctx.send('Success')
        else:
            await ctx.send('Invalid key')


async def setup(bot):
    await bot.add_cog(ChannelControl(bot))
