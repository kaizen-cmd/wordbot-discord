import datetime
import logging
import os

import discord
from dotenv import load_dotenv

from buttons import VoteButton
from WordChainClient import WordChainClient

if ".env" not in os.listdir():
    raise Exception(".env not found")

load_dotenv(".env")

logging.basicConfig(
    filename="app.log",
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger("app")


class App:

    def __init__(self, token) -> None:
        self.CLIENT = self._constrcut_client()
        self.TOKEN = token
        self._add_slash_commands()

    def _constrcut_client(self):
        intents = discord.Intents.default()
        intents.messages = True
        intents.message_content = True
        return WordChainClient(intents=intents, command_prefix="/")

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

            message = self.CLIENT._activate_bot(interaction.guild, interaction.channel)
            await interaction.response.send_message(message)
            if (
                interaction.guild.id != self.CLIENT.SUPPORT_SERVER_ID
                or self.CLIENT.user.name == "word-chain-test"
            ):
                await self.CLIENT.get_channel(
                    self.CLIENT.SUPPORT_SERVER_LOG_CHANNEL_ID
                ).send(f"Server {interaction.guild.name} on boarded")

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

            message = self.CLIENT._deactivate_bot(
                interaction.guild, interaction.channel
            )
            await interaction.response.send_message(message)
            if (
                interaction.guild.id != self.CLIENT.SUPPORT_SERVER_ID
                or self.CLIENT.user.name == "word-chain-test"
            ):
                await self.CLIENT.get_channel(
                    self.CLIENT.SUPPORT_SERVER_LOG_CHANNEL_ID
                ).send(f"Server {interaction.guild.name} de-activated")

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
            await interaction.response.send_message(
                "Wordchain Rules\n"
                "**1**. Check the previous accepted word.\n"
                "**2**. Using the last letter of that write a new word.\n"
                "**3**. NO CONSECUTIVE TURNS ALLOWED.\n"
                "**4**. 7 or more characters in the word = 6 coins 💰.\n"
                "**5**. 6 or lesser characters in the word = 4 coins 💰.\n"
                "**6**. Same starting and ending letter = Additional 2 coins 💰.\n"
                "**7**. Out of turn, wrong word in the chain = **2 coins 💰 will be deducted**.\n"
                "**8**. Word length has to be greater than 3.\n\n"
                "**User Commands**\n"
                "```\n"
                "/help - Get help for wordchain bot\n"
                "/score <username> - Get score of the user\n"
                "/server_leaderboard - Get server rankings\n"
                "/global_leaderboard - Get global rankings\n"
                "/meaning <word>\n"
                "/vote - Get double coins 💰 for next 5 words\n"
                "```\n"
                "**Admin Commands**\n"
                "```\n"
                "/activate - start the game in this channel\n"
                "/deactivate - reset the scores to zero and deactivate\n"
                "/exhaust <letter> - End words beginning with <letter>\n"
                "```\n"
                "Join support server for bugs, suggestions"
            )

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

    def run(self):
        self.CLIENT.run(self.TOKEN)


if __name__ == "__main__":
    app = App(os.getenv("BOT_TOKEN"))
    logger.info("Started Wordchain instance")
    app.run()
