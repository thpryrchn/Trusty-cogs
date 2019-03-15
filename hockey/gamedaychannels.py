import discord
from datetime import datetime
from redbot.core import Config, checks
from .game import Game
from .constants import BASE_URL, CONFIG_ID, TEAMS
from .pickems import Pickems
from .helper import *
from .abc import MixinMeta
import logging

log = logging.getLogger("red.Hockey")
_ = Translator("Hockey", __file__)


class GameDayChannels(MixinMeta):
    """
        This is where the functions to handle creation and deletion 
        of game day channels is stored
    """
    #######################################################################
    # All Game Day Channel Commands

    @commands.group()
    @checks.mod_or_permissions(manage_channels=True)
    @commands.guild_only()
    async def gdc(self, ctx):
        """
            Game Day Channel setup for the server

            You can setup only a single team or all teams for the server
            Game day channels are deleted and created on the day after the game is played
            usually around 9AM PST
        """
        if ctx.invoked_subcommand is None:
            guild = ctx.message.guild
            create_channels = await self.config.guild(guild).create_channels()
            if create_channels is None:
                return
            team = await self.config.guild(guild).gdc_team()
            if team is None:
                team = "None"
            channels = await self.config.guild(guild).gdc()
            category = self.bot.get_channel(await self.config.guild(guild).category())
            delete_gdc = await self.config.guild(guild).delete_gdc()
            if category is not None:
                category = category.name
            if channels is not None:
                created_channels = ""
                for channel in channels:
                    chn = self.bot.get_channel(channel)
                    if chn is not None:
                        if ctx.channel.permissions_for(guild.me).embed_links:
                            created_channels += chn.mention
                        else:
                            created_channels += "#" + chn.name
                    else:
                        created_channels += "<#{}>\n".format(channel)
                if len(channels) == 0:
                    created_channels = "None"
            else:
                created_channels = "None"
            if not ctx.channel.permissions_for(guild.me).embed_links:
                msg = _(
                    "```GDC settings for {guild}\n"
                    "Create Game Day Channels: {channels}\n"
                    "Delete Game Day Channels: {delete}\n"
                    "Team: {team}\n"
                    "Current Channels: {created}\n```"
                )
                await ctx.send(msg)
            if ctx.channel.permissions_for(guild.me).embed_links:
                em = discord.Embed(title=_("GDC settings for ") + guild.name)
                em.colour = await self.bot.db.color()
                em.add_field(name=_("Create Game Day Channels"), value=str(create_channels))
                em.add_field(name=_("Delete Game Day Channels"), value=str(delete_gdc))
                em.add_field(name=_("Team"), value=str(team))
                em.add_field(name=_("Current Channels"), value=created_channels)
                await ctx.send(embed=em)

    @gdc.command(hidden=True, name="test")
    @checks.is_owner()
    async def test_gdc(self, ctx):
        """
            Test checking for new game day channels
        """
        await self.check_new_gdc(self.bot)

    @gdc.command(name="delete")
    async def gdc_delete(self, ctx):
        """
            Delete all current game day channels for the server
        """
        if await self.config.guild(ctx.guild).create_channels():
            await self.delete_gdc(self.bot, ctx.guild)
        await ctx.send(_("Game day channels deleted."))

    @gdc.command(name="create")
    async def gdc_create(self, ctx):
        """
            Creates the next gdc for the server
        """

        if await self.config.guild(ctx.guild).create_channels():
            await self.create_gdc(ctx.guild)
        await ctx.send(_("Game day channels created."))

    @gdc.command(name="toggle")
    async def gdc_toggle(self, ctx):
        """
            Toggles the game day channel creation on this server
        """
        guild = ctx.message.guild
        cur_setting = not await self.config.guild(guild).create_channels()
        verb = _("will") if cur_setting else _("won't")
        msg = _("Game day channels ") + verb + _(" be created on this server.")
        await self.config.guild(guild).create_channels.set(cur_setting)
        await ctx.send(msg)

    @gdc.command(name="category")
    async def gdc_category(self, ctx, category: discord.CategoryChannel):
        """
            Change the category for channel creation. Channel is case sensitive.
        """
        guild = ctx.message.guild

        cur_setting = await self.config.guild(guild).category()

        msg = _("Game day channels will be created in ")
        await self.config.guild(guild).category.set(category.id)
        await ctx.send(msg + category.name)

    @gdc.command(name="autodelete")
    async def gdc_autodelete(self, ctx):
        """
            Toggle's auto deletion of game day channels.
        """
        guild = ctx.message.guild

        cur_setting = await self.config.guild(guild).delete_gdc()
        verb = _("won't") if cur_setting else _("will")
        msg = (
            _("Game day channels ")
            + verb
            + _(" be deleted on this server.\n")
            + _("Note, this may not happen until the next set of games.")
        )
        await self.config.guild(guild).delete_gdc.set(not cur_setting)
        await ctx.send(msg)

    @gdc.command(name="setup")
    async def gdc_setup(
        self,
        ctx,
        team: HockeyTeams,
        category: discord.CategoryChannel = None,
        delete_gdc: bool = True,
    ):
        """
            Setup game day channels for a single team or all teams
            
            Required parameters:
            `team` must use quotes if a space is in the name will search for partial team name
            Optional Parameters:
            `category` must use quotes if a space is in the name will default to current category
            `delete_gdc` will tell the bot whether or not to delete game day channels automatically
            must be either `True` or `False` and a category must be provided
        """
        guild = ctx.message.guild
        if guild is None:
            await ctx.send("This needs to be done in a server.")
            return
        if category is None:
            category = guild.get_channel(ctx.message.channel.category_id)
        if not category.permissions_for(guild.me).manage_channels:
            await ctx.send(_("I don't have manage channels permission!"))
            return
        await self.config.guild(guild).category.set(category.id)
        await self.config.guild(guild).gdc_team.set(team)
        await self.config.guild(guild).delete_gdc.set(delete_gdc)
        if team.lower() != "all":
            await self.create_gdc(guild)
        else:
            game_list = await Game.get_games()
            for game in game_list:
                await self.create_gdc(guild, game)
        await ctx.send(_("Game Day Channels for ") + team + _("setup in ") + category.name)

    @gdc.command()
    @checks.is_owner()
    async def setcreated(self, ctx, created: bool):
        """
            Sets whether or not the game day channels have been created
        """
        await self.config.created_gdc.set(created)
        await ctx.send(_("created_gdc set to ") + str(created))

    @gdc.command()
    @checks.is_owner()
    async def cleargdc(self, ctx):
        """
            Checks for manually deleted channels from the GDC channel list 
            and removes them
        """
        guild = ctx.message.guild
        good_channels = []
        for channels in await self.config.guild(guild).gdc():
            channel = self.bot.get_channel(channels)
            if channel is None:
                await self.config._clear_scope(Config.CHANNEL, str(channels))
                log.info("Removed the following channels" + str(channels))
                continue
            else:
                good_channels.append(channel.id)
        await self.config.guild(guild).gdc.set(good_channels)

    async def get_chn_name(self, game):
        """
            Creates game day channel name
        """
        timestamp = utc_to_local(game.game_start)
        chn_name = "{}-vs-{}-{}-{}-{}".format(
            game.home_abr, game.away_abr, timestamp.year, timestamp.month, timestamp.day
        )
        return chn_name.lower()

    async def check_new_gdc(self):
        # config = self.config.get_conf(None, CONFIG_ID, cog_name="Hockey")
        game_list = await Game.get_games()  # Do this once so we don't spam the api
        for guilds in await self.self.config.all_guilds():
            guild = self.bot.get_guild(guilds)
            if guild is None:
                continue
            if not await self.config.guild(guild).create_channels():
                continue
            team = await self.config.guild(guild).gdc_team()
            if team != "all":
                next_games = await Game.get_games_list(team, datetime.now())
                if next_games != []:
                    next_game = await Game.from_url(next_games[0]["link"])
                if next_game is None:
                    continue
                chn_name = await self.get_chn_name(next_game)
                try:
                    cur_channels = await self.config.guild(guild).gdc()
                    cur_channel = bot.get_channel(cur_channels[0])
                except Exception as e:
                    log.error("Error checking new GDC", exc_info=True)
                    cur_channel = None
                if cur_channel is None:
                    await self.create_gdc(bot, guild)
                elif cur_channel.name != chn_name.lower():
                    await self.delete_gdc(bot, guild)
                    await self.create_gdc(bot, guild)

            else:
                await self.delete_gdc(bot, guild)
                for game in game_list:
                    await self.create_gdc(bot, guild, game)

    async def create_gdc(self, guild, game_data=None):
        """
            Creates a game day channel for the given game object
            if no game object is passed it looks for the set team for the guild
            returns None if not setup
        """
        # config = self.config.get_conf(None, CONFIG_ID, cog_name="Hockey")
        category = self.bot.get_channel(await self.config.guild(guild).category())
        if category is None:
            # Return none if there's no category to create the channel
            return
        if game_data is None:
            team = await self.config.guild(guild).gdc_team()

            next_games = await Game.get_games_list(team, datetime.now())
            if next_games != []:
                next_game = await Game.from_url(next_games[0]["link"])
                if next_game is None:
                    return
            else:
                # Return if no more games are playing for this team
                return
        else:
            team = game_data.home_team
            next_game = game_data

        chn_name = await self.get_chn_name(next_game)
        try:
            new_chn = await guild.create_text_channel(chn_name, category=category)
        except Exception as e:
            log.error("Error creating channels in {}".format(guild.name), exc_info=True)
            return
        cur_channels = await self.config.guild(guild).gdc()
        if cur_channels is None:
            cur_channels = []
        cur_channels.append(new_chn.id)
        await self.config.guild(guild).gdc.set(cur_channels)
        await self.config.guild(guild).create_channels.set(True)
        await self.config.channel(new_chn).team.set([team])
        delete_gdc = await self.config.guild(guild).delete_gdc()
        await self.config.channel(new_chn).to_delete.set(delete_gdc)

        # Gets the timezone to use for game day channel topic
        # timestamp = datetime.strptime(next_game.game_start, "%Y-%m-%dT%H:%M:%SZ")
        guild_team = await self.config.guild(guild).gdc_team()
        channel_team = guild_team if guild_team != "all" else next_game.home_team
        timezone = (
            TEAMS[channel_team]["timezone"]
            if channel_team in TEAMS
            else TEAMS[next_game.away_team]["timezone"]
        )
        time_string = utc_to_local(next_game.game_start, timezone).strftime(
            "%A %B %d, %Y at %I:%M %p %Z"
        )

        game_msg = (
            f"{next_game.away_team} {next_game.away_emoji} @ "
            f"{next_game.home_team} {next_game.home_emoji} {time_string}"
        )

        await new_chn.edit(topic=game_msg)
        if new_chn.permissions_for(guild.me).embed_links:
            em = await next_game.game_state_embed()
            preview_msg = await new_chn.send(embed=em)
        else:
            preview_msg = await new_chn.send(await next_game.game_state_text())

        # Create new pickems object for the game
        await Pickems.create_pickem_object(guild, preview_msg, new_chn, next_game)

        if new_chn.permissions_for(guild.me).manage_messages:
            await preview_msg.pin()
        if new_chn.permissions_for(guild.me).add_reactions:
            try:
                await preview_msg.add_reaction(next_game.away_emoji[2:-1])
                await preview_msg.add_reaction(next_game.home_emoji[2:-1])
            except Exception as e:
                log.debug("cannot add reactions")

    async def delete_gdc(self, guild):
        """
            Deletes all game day channels in a given guild
        """
        # config = self.config.get_conf(None, CONFIG_ID, cog_name="Hockey")
        channels = await self.config.guild(guild).gdc()

        for channel in channels:
            chn = self.bot.get_channel(channel)
            if chn is None:
                try:
                    await self.config._clear_scope(self.config.CHANNEL, str(chn))
                except:
                    pass
                continue
            if not await self.config.channel(chn).to_delete():
                continue
            try:
                await self.config.channel(chn).clear()
                await chn.delete()
            except Exception as e:
                log.error("Cannot delete GDC channels")
        await self.config.guild(guild).gdc.set([])
