import discord

from elements import VoteButton
from WordChainClient import WordChainClient
from logging_config import get_logger

logger = get_logger(__name__)


class App:

    def __init__(self, token, client) -> None:
        self.CLIENT = client
        self.TOKEN = token
        self._add_slash_commands()

    def _add_slash_commands(self):

        @self.CLIENT.tree.command(
            name="activate", description="start the word chain game in this channel"
        )
        async def activate(interaction: discord.Interaction):
            if interaction.user.bot:
                return
            if not interaction.user.guild_permissions.administrator:
                await interaction.response.send_message(
                    "Ask a server admin to run this command"
                )
                return

            embed = self.CLIENT._activate_bot(interaction.guild, interaction.channel)
            await interaction.response.send_message(embed=embed, view=VoteButton())
            logger.info(f"Activated game in server {interaction.guild.name}")
            if (
                interaction.guild.id != self.CLIENT.SUPPORT_SERVER_ID
                or self.CLIENT.user.name == "word-chain-test"
            ):
                await self.CLIENT.get_channel(
                    WordChainClient.SUPPORT_SERVER_LOG_CHANNEL_ID
                ).send(
                    f"[ACTIVATED] Server {interaction.guild.name} | Members: {interaction.guild.member_count}"
                )

        @self.CLIENT.tree.command(
            name="deactivate",
            description="reset the word chain game and set all scores to zero",
        )
        async def deactivate(interaction: discord.Interaction):
            if interaction.user.bot:
                return
            if not interaction.user.guild_permissions.administrator:
                await interaction.response.send_message(
                    "Ask a server admin to run this command"
                )
                return

            embed = self.CLIENT._deactivate_bot(interaction.guild, interaction.channel)
            await interaction.response.send_message(embed=embed, view=VoteButton())
            logger.info(f"Deactivated game in server {interaction.guild.name}")
            if (
                interaction.guild.id != self.CLIENT.SUPPORT_SERVER_ID
                or self.CLIENT.user.name == "word-chain-test"
            ):
                await self.CLIENT.get_channel(
                    WordChainClient.SUPPORT_SERVER_LOG_CHANNEL_ID
                ).send(
                    f"[DE-ACTIVATED] Server {interaction.guild.name} | Members: {interaction.guild.member_count}"
                )

        @self.CLIENT.tree.command(
            name="global_leaderboard", description="get global leaders in wordchain"
        )
        async def global_leaderboard(interaction: discord.Interaction):
            if interaction.user.bot:
                return
            await interaction.response.defer(thinking=True)
            message = await self.CLIENT._construct_and_send_global_leader_board()
            if type(message) == str:
                await interaction.followup.send(message)
                return
            await interaction.followup.send(embed=message, view=VoteButton())

        @self.CLIENT.tree.command(
            name="vote",
            description="vote on top.gg to get double coins 💰 for next 5 words",
        )
        async def send_vote_link(interaction: discord.Interaction):
            if interaction.user.bot:
                return
            await interaction.response.send_message(
                "Vote on https://top.gg/bot/1225490759432798320 to get double coins 💰 on next 5 accepted words"
            )

        @self.CLIENT.tree.command(
            name="help",
            description="get help for the bot",
        )
        async def help(interaction: discord.Interaction):
            if interaction.user.bot:
                return
            embed = self.CLIENT.get_help_embed()
            await interaction.response.send_message(embed=embed, view=VoteButton())

        @self.CLIENT.tree.command(
            name="exhaust",
            description="exhaust words starting with the given letter -> choices <a-z>",
        )
        async def exhaust_letter(interaction: discord.Interaction, letter: str):
            if interaction.user.bot:
                return
            if not interaction.user.guild_permissions.administrator:
                await interaction.response.send_message(
                    "Ask a server admin to run this command"
                )
                return
            new_letter = self.CLIENT._exhaust_words_beginning_with(
                letter, interaction.guild_id
            )
            await interaction.response.send_message(
                f"Words starting with `{letter}` exhausted. A new letter will be suggested whenever a word ends in this letter. New letter is `{new_letter}`"
            )
            logger.info(
                f"Exhausted words starting with {letter} in server {interaction.guild.name}"
            )

        @self.CLIENT.tree.command(
            name="score", description="get score of the mentioned user"
        )
        async def score(interaction: discord.Interaction, user: discord.User | None):
            if interaction.user.bot:
                return
            if not user:
                user = interaction.user
            message = self.CLIENT._send_user_score(user, interaction.guild)
            if type(message) == str:
                await interaction.response.send_message(message)
                return
            await interaction.response.send_message(embed=message, view=VoteButton())

        @self.CLIENT.tree.command(
            name="server_leaderboard",
            description="get leaderboard for the current server",
        )
        async def server_leaderboard(interaction: discord.Interaction):
            if interaction.user.bot:
                return
            await interaction.response.defer(thinking=True)
            message = await self.CLIENT._construct_and_send_leader_board(
                interaction.guild
            )
            if type(message) == str:
                await interaction.followup.send(message)
                return
            await interaction.followup.send(embed=message, view=VoteButton())

        @self.CLIENT.tree.command(
            name="meaning",
            description="get meaning of the word",
        )
        async def meaning(interaction: discord.Interaction, word: str):
            if interaction.user.bot:
                return
            message = self.CLIENT._send_meaning(word)
            if type(message) == str:
                await interaction.response.send_message(message)
                return
            await interaction.response.send_message(embed=message)

        @self.CLIENT.tree.command(
            name="shop", description="Check out the gamingrefree shop"
        )
        async def shop(interaction: discord.Interaction):
            if interaction.user.bot:
                return
            await interaction.response.send_message("Launching SOON!")

        @self.CLIENT.tree.command(
            name="top_servers", description="Top servers to score the most points"
        )
        async def top_servers(interaction: discord.Interaction):
            if interaction.user.bot:
                return
            await interaction.response.defer(thinking=True)
            message = await self.CLIENT._construct_and_send_top_servers()
            if type(message) == str:
                await interaction.followup.send(message)
                return
            await interaction.followup.send(embed=message, view=VoteButton())

    def run(self):
        logger.info("Running the bot")
        self.CLIENT.run(self.TOKEN)
