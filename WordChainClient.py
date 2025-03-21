import asyncio
import json
import os

import discord
from discord.ext import commands
import aiohttp

from elements import GamingRefreeEmbed
from logging_config import get_logger

logger = get_logger(__name__)


class WordChainClient(commands.AutoShardedBot):

    SLAV_USER_ID = int(os.getenv("SLAV_USER_ID"))
    SUPPORT_SERVER_ID = int(os.getenv("SUPPORT_SERVER_ID"))
    SUPPORT_SERVER_LOG_CHANNEL_ID = int(os.getenv("SUPPORT_SERVER_LOG_CHANNEL_ID"))
    POINTS_REACTIONS_MAP = {
        4: "4️⃣",
        6: "6️⃣",
        8: "8️⃣",
        12: "🔥",
        16: "🤑",
    }

    def __init__(self, db, insights, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.db = db
        self.insights = insights
        # self.shard_count = 2

        f = open("server_channel_mapping.json", "r")
        self.server_channel_mapping = json.loads(f.read())
        f.close()

    async def on_ready(self):
        logger.info("Bot is ready")
        await self.change_presence(
            status=discord.Status.do_not_disturb,
            activity=discord.Game(
                name=f"WordChain in {len(self.guilds)} servers",
            ),
        )
        await self.tree.sync()

    async def on_message(self, message: discord.message.Message):

        if message.author.bot:
            return

        try:
            author = message.author
            if author.id == self.user.id:
                return

            content = message.content
            content = content.lower()
            if not self._validate_message(content):
                return

            server = message.guild
            channel = message.channel
            if self.server_channel_mapping.get(str(server.id)) != channel.id:
                return

            result, string_message, points = self.db.try_play_word(
                server_id=server.id, word=content, player_id=author.id
            )

            coroutines = list()
            if result:
                streak_count, streak_message = self.db.update_user_streak(
                    server_id=server.id, player_id=author.id
                )
                coroutines.append(
                    message.add_reaction(WordChainClient.POINTS_REACTIONS_MAP[points])
                )
                if len(string_message) == 1:
                    coroutines.append(
                        message.reply(
                            f"Words beginning with {content[-1]} are over. New character is `{string_message}`"
                        )
                    )
                if streak_count != -1 and len(streak_message) != 0:
                    coroutines.append(message.reply(streak_message))

            else:
                coroutines.append(message.add_reaction("❌"))
                coroutines.append(message.reply(string_message))

            await asyncio.gather(*coroutines)

        except Exception as e:
            logger.error(
                f"[WORD PLAY ERROR]: {message.content} == {e} == {message.guild.name}",
                exc_info=True,
            )

        self.db.refresh_words(server_id=server.id)
        self.insights.send()

    async def on_guild_remove(self, server: discord.guild.Guild):
        try:
            self.db.deboard_server(server.id)
        except Exception as e:
            logger.error(f"Error deboarding server {server.id}: {e}", exc_info=True)
        await self.change_presence(
            status=discord.Status.do_not_disturb,
            activity=discord.Game(
                name=f"WordChain in {len(self.guilds)} servers",
            ),
        )
        await self.get_channel(WordChainClient.SUPPORT_SERVER_LOG_CHANNEL_ID).send(
            f"[KICKED] Server {server.name} | Members: {server.member_count}"
        )

    async def on_guild_join(self, server: discord.Guild):
        logger.info(f"Joined new guild: {server.name}")
        await self.change_presence(
            status=discord.Status.do_not_disturb,
            activity=discord.Game(
                name=f"WordChain in {len(self.guilds)} servers",
            ),
        )
        await self.get_channel(WordChainClient.SUPPORT_SERVER_LOG_CHANNEL_ID).send(
            f"[INVITED] Server {server.name} | Members: {server.member_count}"
        )

    async def _construct_and_send_top_servers(self):
        result, data = self.db.get_top_servers()
        if not result:
            return data
        embed = GamingRefreeEmbed(title="Top Servers")
        for server_row in data:
            rank, server_id, score = server_row
            embed.add_field(
                value=f"{score} coins 💰",
                name=f"#{rank} {self.get_guild(int(server_id)).name}",
                inline=False,
            )
        return embed

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
            logger.error(
                f"Error deactivating bot for server {server.id}: {e}", exc_info=True
            )
        embed = GamingRefreeEmbed()
        embed.title = "Game stopped and scores reset"
        embed.description = (
            "Wordchain resetted and deactivated  ⭕️, `/activate` to reactivate"
        )
        return embed

    def _activate_bot(self, server: discord.Guild, channel):
        self.server_channel_mapping[str(server.id)] = channel.id
        f = open("server_channel_mapping.json", "w")
        f.write(json.dumps(self.server_channel_mapping))
        f.close()
        if not self.db.is_server_onboard(server.id):
            self.db.onboard_server(server.id)
        embed = GamingRefreeEmbed()
        embed.title = "Game started!"
        embed.description = (
            "Wordchain activated, type a word ✅ , `/help` for rules and support"
        )
        return embed

    async def _construct_and_send_leader_board(self, server: discord.Guild):
        result, data = self.db.leaderboard(server_id=server.id)
        if not result:
            return data
        embed = GamingRefreeEmbed(
            title=f"{server.name} Leaderboard",
        )
        coroutines = list()
        for user_row in data:
            rank, id, score = user_row
            coroutines.append(self.fetch_user(id))
        users = await asyncio.gather(*coroutines)
        for user, user_row in zip(users, data):
            rank, id, score = user_row
            streak_count = self.db.get_streak_count(str(server.id), str(id))
            try:
                if not embed.thumbnail.url:
                    embed.set_thumbnail(url=user.avatar.url)
            except Exception as e:
                logger.error(
                    f"[SERVER LEADERBOARD COMMAND] Error in setting leaderboard thumbnail for user {user.global_name}",
                    exc_info=True,
                )
            embed.add_field(
                value=f"{score} coins 💰 | {streak_count} days streak 🔥",
                name=f"#{rank} {user.global_name}",
                inline=False,
            )

        return embed

    async def _construct_and_send_global_leader_board(self):
        result, data = self.db.get_global_leaderboard()
        if not result:
            return data

        embed = GamingRefreeEmbed(title=f"Global leaderboard (Realtime)")

        coroutines = list()
        for user_row in data:
            rank, id, score, server_id = user_row
            coroutines.append(self.fetch_user(id))
        users = await asyncio.gather(*coroutines)
        for user, user_row in zip(users, data):
            rank, id, score, server_id = user_row
            streak_count = self.db.get_streak_count(server_id, id)
            try:
                if not embed.thumbnail.url:
                    embed.set_thumbnail(url=user.avatar.url)
            except Exception as e:
                logger.error(
                    f"[SERVER LEADERBOARD COMMAND] Error in setting leaderboard thumbnail for user {user.global_name}",
                    exc_info=True,
                )
            embed.add_field(
                value=f"{score} coins 💰 | {streak_count} days streak 🔥",
                name=f"#{rank} {user.global_name}",
                inline=False,
            )

        return embed

    def _send_user_score(self, author: discord.User, server: discord.Guild):
        result, data = self.db.get_score(server.id, author.id)
        streak_count = self.db.get_streak_count(server.id, author.id)
        if not result:
            return data
        id, score, rank = data
        embed = GamingRefreeEmbed(title=f"{author.global_name}'s score")
        embed.add_field(
            value=f"**{score}** coins 💰 | **{streak_count} days streak** 🔥",
            name=f"Rank {rank}",
            inline=False,
        )
        embed.set_thumbnail(url=author.avatar.url if author.avatar else None)
        return embed

    async def _send_meaning(self, word: str):
        if word.isalpha():
            client = aiohttp.client.ClientSession()
            response = await client.get(
                f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
            )
            if response.status == 400:
                return f"The language expert is not avaialable at the moment"

            try:
                meaning = (await response.json())[0]["meanings"][0]["definitions"][0][
                    "definition"
                ]
                embed = GamingRefreeEmbed(title=f"Meaning of the word {word}")
                embed.add_field(name=word, value=meaning)
                return embed
            except:
                return f"The language expert is not avaialable at the moment"
        return "Invalid word"

    def get_help_embed(self):
        embed = GamingRefreeEmbed()
        embed.description = (
            "Wordchain Rules\n"
            "- Check the previous accepted word.\n"
            "- Using the last letter of that write a new word.\n"
            "- NO CONSECUTIVE TURNS ALLOWED.\n"
            "- 7 or more characters in the word = 6 coins 💰.\n"
            "- 6 or lesser characters in the word = 4 coins 💰.\n"
            "- Same starting and ending letter = Additional 2 coins 💰.\n"
            "- Out of turn, wrong word in the chain = **2 coins 💰 will be deducted**.\n"
            "- Word length has to be greater than 3.\n\n"
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
        return embed

    def _validate_message(self, content: str):
        words = content.lower().split(" ")
        if len(words) > 1:
            return False
        word = words[0]
        return word.isalpha()
