import json
import logging.handlers
import os

import discord
import requests
from discord.ext import commands

from MultiServerWordChainDB import MultiServerWordChainDB

import logging

logger = logging.getLogger(__name__)


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
        await self.tree.sync()

    async def on_message(self, message: discord.message.Message):

        try:
            author = message.author
            if author.id == self.user.id:
                return

            server = message.guild
            channel = message.channel
            if self.server_channel_mapping.get(str(server.id)) != channel.id:
                return

            content = message.content
            content = content.lower()
            if not self._validate_message(content):
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
            logger.error(
                f"MESSAGE PROCESSING: {message.content} == {e} == {message.guild.name}"
            )

    async def on_guild_remove(self, server: discord.guild.Guild):
        self.db.deboard_server(server.id)
        await self.get_channel(WordChainClient.SUPPORT_SERVER_LOG_CHANNEL_ID).send(
            f"Server {server.name} kicked the bot"
        )
        await self.change_presence(
            status=discord.Status.do_not_disturb,
            activity=discord.Game(
                name=f"WordChain in {len(self.guilds)} servers",
            ),
        )

    async def on_guild_join(self, server: discord.Guild):
        await self.change_presence(
            status=discord.Status.do_not_disturb,
            activity=discord.Game(
                name=f"WordChain in {len(self.guilds)} servers",
            ),
        )

    def _exhaust_words_beginning_with(self, old_letter, server_id):
        self.db.curr.execute(
            f"UPDATE words_{server_id} SET isUsed=1 WHERE word LIKE '{old_letter}%'"
        ).fetchone()
        self.db.conn.commit()
        new_letter = self.db._change_letter(server_id=server_id)
        return new_letter

    def _deactivate_bot(self, server: discord.Guild, channel):
        if self.server_channel_mapping.get(str(server.id)):
            del self.server_channel_mapping[str(server.id)]
            f = open("server_channel_mapping.json", "w")
            f.write(json.dumps(self.server_channel_mapping))
            f.close()
        try:
            self.db.deboard_server(server_id=server.id)
        except Exception as e:
            pass
        return "Wordchain resetted and deactivated  ⭕️, `/activate` to reactivate"

    def _activate_bot(self, server: discord.Guild, channel):
        self.server_channel_mapping[str(server.id)] = channel.id
        f = open("server_channel_mapping.json", "w")
        f.write(json.dumps(self.server_channel_mapping))
        f.close()
        if not self.db.is_server_onboard(server.id):
            self.db.onboard_server(server.id)
        return "Wordchain activated, type a word ✅ , ```/help``` for rules and support"

    async def _construct_and_send_leader_board(self, server: discord.Guild):
        result, data = self.db.leaderboard(server.id)
        if not result:
            return data

        embed = discord.Embed()
        embed.title = f"{server.name} leaderboard"
        embed.colour = discord.Color.purple()

        for user_row in data:
            rank, id, score = user_row
            user = await self.fetch_user(id)
            try:
                if not embed.thumbnail.url:
                    embed.set_thumbnail(url=user.avatar.url)
            except:
                logger.error(
                    f"Error in setting leaderboard thumbnail for user {user.global_name}"
                )
            embed.add_field(
                value=f"#{rank}.    @{user.global_name}    {score} points",
                name="",
                inline=False,
            )

        embed.set_footer(text=f"GamingRefree made this")
        return embed

    def _send_user_score(self, author: discord.User, server: discord.Guild):
        result, data = self.db.get_score(server.id, author.id)
        if not result:
            return data
        id, score, rank = data
        embed = discord.Embed(title=f"{author.global_name}'s score")
        embed.add_field(
            value=f"Rank {rank}.    @{author.global_name}    {score} points",
            name="",
            inline=False,
        )
        embed.set_thumbnail(url=author.avatar.url)
        embed.set_footer(text=f"GamingRefree made this")
        embed.colour = discord.Color.dark_teal()
        return embed

    def _send_meaning(self, word: str):
        if word.isalpha():
            response = requests.get(
                f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
            )
            if response.status_code == 400:
                return f"The language expert is not avaialable at the moment"

            try:
                meaning = response.json()[0]["meanings"][0]["definitions"][0][
                    "definition"
                ]
                embed = discord.Embed(title=f"Meaning of the word {word}")
                embed.add_field(name=word, value=meaning)
                embed.colour = discord.Color.dark_blue()
                embed.set_footer(text=f"GamingRefree made this")
                return embed
            except:
                return f"The language expert is not avaialable at the moment"
        return "Invalid word"

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
            "@GamingRefree myscore\n"
            "@GamingRefree score\n"
            "@GamingRefree meaning <word>\n"
            "```\n"
            "**Slash Commands**\n"
            "```\n"
            "/vote - Get double points for next 5 words\n"
            "/global_leaderboard - Get global rankings\n"
            "```\n"
            "**Admin Commands**\n"
            "```\n"
            "@GamingRefree activate\n"
            "@GamingRefree deactivate\n"
            "@GamingRefree exhaust <letter> - End words beginning with <letter>\n"
            "```\n"
            "Join support server for bugs, suggestions"
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
