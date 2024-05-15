import json
import logging.handlers
import os

import discord
import requests
from discord.ext import commands

from MultiServerWordChainDB import MultiServerWordChainDB

import logging

logging.basicConfig(
    filename="ishqzaade_messages.log",
    level=logging.ERROR,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger("ISHQZAADE MESSAGES")


class WordChainClient(commands.AutoShardedBot):

    SLAV_USER_ID = int(os.getenv("SLAV_USER_ID"))
    SUPPORT_SERVER_ID = int(os.getenv("SUPPORT_SERVER_ID"))
    SUPPORT_SERVER_LOG_CHANNEL_ID = int(os.getenv("SUPPORT_SERVER_LOG_CHANNEL_ID"))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.db = MultiServerWordChainDB()

        f = open("server_channel_mapping.json", "r")
        self.server_channel_mapping = json.loads(f.read())
        f.close()

    async def on_ready(self):
        await self.change_presence(
            status=discord.Status.do_not_disturb,
            activity=discord.Game(
                name=f"WordChain in {len(self.guilds)} servers",
            ),
        )

    async def on_message(self, message: discord.message.Message):

        try:
            if message.guild.id == 1007908356964491274:
                logger.error(message.content)

            author = message.author
            if author.id == self.user.id:
                return

            if (
                message.mentions
                and message.mentions[0].id == self.user.id
                and len(message.content.split(" ")) > 1
            ):
                args = message.content.split(" ")
                command = args[1]
                if (
                    command == "activate"
                    and message.author.guild_permissions.administrator
                ):
                    await self._activate_bot(message)

                elif (
                    command == "deactivate"
                    and message.author.guild_permissions.administrator
                ):
                    await self._deactivate_bot(message)

                elif (
                    command == "exhaust"
                    and len(args) == 3
                    and len(args[2]) == 1
                    and message.author.guild_permissions.administrator
                ):
                    await self._exhaust_words_beginning_with(message)

                elif command == "score":
                    await self._construct_and_send_leader_board(message)

                elif command == "myscore":
                    await self._send_user_score(message)

                elif command == "help":
                    await self._send_help(message)

                elif command == "meaning" and len(args) == 3:
                    await self._send_meaning(message)

            else:

                content = message.content
                content = content.lower()
                if not self._validate_message(content):
                    return

                server = message.guild
                channel = message.channel
                if self.server_channel_mapping.get(str(server.id)) != channel.id:
                    return

                result, string_message = self.db.try_play_word(
                    server_id=server.id, word=content, player_id=author.id
                )

                if result:
                    await message.add_reaction("✅")
                    if len(string_message) == 1:
                        await message.reply(
                            f"Words beginning with {content[-1]} are over. New character is `{string_message}`"
                        )

                else:
                    await message.add_reaction("❌")
                    await message.reply(string_message)
        except Exception as e:
            logger.error(e)

    async def on_guild_remove(self, server: discord.guild.Guild):
        self.db.deboard_server(server.id)
        await self.get_channel(WordChainClient.SUPPORT_SERVER_LOG_CHANNEL_ID).send(
            f"Server {server.name} kicked the bot"
        )

    async def _exhaust_words_beginning_with(self, message: discord.Message):
        old_letter = message.content.split(" ")[2].lower()
        self.db.curr.execute(
            f"UPDATE words_{message.guild.id} SET isUsed=1 WHERE word LIKE '{old_letter}%'"
        ).fetchone()
        self.db.conn.commit()
        new_letter = self.db._change_letter(server_id=message.guild.id)
        await message.reply(
            f"Words starting with `{old_letter}` exhausted. A new letter will be suggested whenever a word ends in this letter. New letter is `{new_letter}`"
        )

    async def _deactivate_bot(self, message: discord.Message):
        if self.server_channel_mapping.get(str(message.guild.id)):
            del self.server_channel_mapping[str(message.guild.id)]
            f = open("server_channel_mapping.json", "w")
            f.write(json.dumps(self.server_channel_mapping))
            f.close()
        try:
            self.db.deboard_server(server_id=message.guild.id)
        except Exception as e:
            pass
        await message.channel.send(
            "Wordchain resetted and deactivated  ⭕️, `@WordChainAdmin activate` to reactivate"
        )
        if (
            message.guild.id != WordChainClient.SUPPORT_SERVER_ID
            or self.user.name == "word-chain-test"
        ):
            await self.get_channel(WordChainClient.SUPPORT_SERVER_LOG_CHANNEL_ID).send(
                f"Server {message.guild.name} de-activated"
            )

    async def _activate_bot(self, message: discord.Message):
        self.server_channel_mapping[str(message.guild.id)] = message.channel.id
        f = open("server_channel_mapping.json", "w")
        f.write(json.dumps(self.server_channel_mapping))
        f.close()
        server = message.guild
        if not self.db.is_server_onboard(server.id):
            self.db.onboard_server(server.id)
        await message.channel.send(
            "Wordchain activated, type a word ✅ , ```@WordChainAdmin help``` for rules and support"
        )
        if (
            server.id != WordChainClient.SUPPORT_SERVER_ID
            or self.user.name == "word-chain-test"
        ):
            await self.get_channel(WordChainClient.SUPPORT_SERVER_LOG_CHANNEL_ID).send(
                f"Server {message.guild.name} on boarded"
            )

    async def _construct_and_send_leader_board(self, message: discord.Message):
        result, data = self.db.leaderboard(message.guild.id)
        if not result:
            await message.reply(data)
            return

        embed = discord.Embed()
        embed.title = f"{message.guild.name} leaderboard"
        embed.colour = discord.Color.purple()

        for user_row in data:
            rank, id, score = user_row
            user = await self.fetch_user(id)
            if not embed.thumbnail.url:
                embed.set_thumbnail(url=user.avatar.url)
            embed.add_field(
                value=f"#{rank}.    @{user.global_name}    {score} points",
                name="",
                inline=False,
            )

        embed.set_footer(text=f"WordChainAdmin made this")
        await message.reply(embed=embed)

    async def _send_user_score(self, message: discord.Message):
        result, data = self.db.get_score(message.guild.id, message.author.id)
        if not result:
            await message.reply(data)
            return
        id, score, rank = data
        embed = discord.Embed(title=f"{message.author.global_name}'s score")
        embed.add_field(
            value=f"Rank {rank}.    @{message.author.global_name}    {score} points",
            name="",
            inline=False,
        )
        embed.set_thumbnail(url=message.author.avatar.url)
        embed.set_footer(text=f"WordChainAdmin made this")
        embed.colour = discord.Color.dark_teal()
        await message.reply(embed=embed)

    async def _send_meaning(self, message: discord.Message):
        word = message.content.split(" ")[2]
        if word.isalpha():
            response = requests.get(
                f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
            )
            if response.status_code == 400:
                await message.reply(
                    f"Sorry pal! No meaning found for **{word}**. Dictionary api down"
                )
            try:
                meaning = response.json()[0]["meanings"][0]["definitions"][0][
                    "definition"
                ]
                embed = discord.Embed(title=f"Meaning of the word {word}")
                embed.add_field(name=word, value=meaning)
                embed.colour = discord.Color.dark_blue()
                embed.set_footer(text=f"WordChainAdmin made this")
                await message.reply(embed=embed)
            except:
                await message.reply(
                    f"Sorry pal! No meaning found for **{word}**. It could be a proper noun."
                )
            return
        await message.reply("Invalid word")

    async def _send_help(self, message: discord.Message):
        await message.reply(
            "Wordchain Rules\n"
            "**1**. Check the previous accepted word.\n"
            "**2**. Using the last letter of that write a new word.\n"
            "**3**. NO CONSECUTIVE TURNS ALLOWED.\n"
            "**4**. 7 or more characters in the word = 6 points.\n"
            "**5**. 6 or lesser characters in the word = 4 points.\n"
            "**6**. Same starting and ending letter = Additional 2 points.\n"
            "**7**. Out of turn, wrong word in the chain = **2 points will be deducted**.\n"
            "**8**. Word length has to be greater than 3.\n\n"
            "**User Commands**\n"
            "```\n"
            "@WordChainAdmin myscore\n"
            "@WordChainAdmin score\n"
            "@WordChainAdmin meaning <word>\n"
            "```\n\n"
            "**Admin Commands**\n"
            "```\n"
            "@WordChainAdmin activate\n"
            "@WordChainAdmin deactivate\n"
            "@WordChainAdmin exhaust <letter> - End words beginning with <letter>\n"
            "```\n"
            "Support server: https://discord.gg/ftZJcGvsvP"
        )

    def _validate_message(self, content: str):
        words = content.lower().split(" ")
        if len(words) > 1:
            return False
        word = words[0]
        return word.isalpha()


def construct_client():
    intents = discord.Intents.default()
    intents.messages = True
    intents.message_content = True
    client = WordChainClient(intents=intents, command_prefix="/")
    return client
