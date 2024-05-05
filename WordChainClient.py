import json

import discord
import requests
from discord import app_commands
from discord.ext import commands

from MultiServerWordChainDB import MultiServerWordChainDB


db = MultiServerWordChainDB()


class WordChainClient(commands.Bot):
    def __init__(self, *args, **kwargs):
        global db
        super().__init__(*args, **kwargs)
        self.db = db

        f = open("server_channel_mapping.json", "r")
        self.server_channel_mapping = json.loads(f.read())
        f.close()

    async def on_ready(self):
        try:
            await self.tree.sync()
        except:
            pass

    @staticmethod
    def validate_message(content: str):
        words = content.lower().split(" ")
        if len(words) > 1:
            return False
        word = words[0]
        return word.isalpha()

    async def on_message(self, message: discord.message.Message):

        author = message.author
        if author.id == self.user.id:
            return

        if (
            message.mentions
            and message.mentions[0].id == self.user.id
            and len(message.content.split(" ")) == 2
        ):
            if message.content.split(" ")[1] == "activate":
                self.server_channel_mapping[str(message.guild.id)] = message.channel.id
                f = open("server_channel_mapping.json", "w")
                f.write(json.dumps(self.server_channel_mapping))
                f.close()
                server = message.guild
                if not self.db.is_server_onboard(server.id):
                    self.db.onboard_server(server.id)
                await message.channel.send("Wordchain activated, type a word ✅ ")
                try:
                    # prod message
                    await self.get_channel(1236196728613371966).send(
                        f"Server {message.guild.name} on boarded"
                    )
                except:
                    # test message
                    await self.get_channel(1234117670996148246).send(
                        f"Server {message.guild.name} on boarded"
                    )

            elif (
                message.content.split(" ")[1] == "deactivate"
                and message.author.id == 462682564281499659  # slav's user id
            ):
                if client.server_channel_mapping.get(str(message.guild.id)):
                    del client.server_channel_mapping[str(message.guild.id)]
                    f = open("server_channel_mapping.json", "w")
                    f.write(json.dumps(client.server_channel_mapping))
                    f.close()
                try:
                    db.deboard_server(server_id=message.guild.id)
                except Exception as e:
                    pass
                await message.channel.send(
                    "Wordchain resetted and deactivated  ⭕️, `/activate to reactivate`"
                )
                try:
                    # prod message
                    await client.get_channel(1236196728613371966).send(
                        f"Server {message.guild.name} de-activated"
                    )
                except:
                    # test message
                    await client.get_channel(1234117670996148246).send(
                        f"Server {message.guild.name} de-activated"
                    )

        else:

            content = message.content
            content = content.lower()
            if not WordChainClient.validate_message(content):
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
                    await channel.send(
                        f"Words beginning with {content[-1]} are over. New character is {string_message}"
                    )

            else:
                await message.add_reaction("❌")
                await message.reply(string_message)

    async def on_guild_remove(self, server: discord.guild.Guild):
        self.db.deboard_server(server.id)
        try:
            # prod message
            await self.get_channel(1236196728613371966).send(
                f"Server {server.name} kicked the bot"
            )
        except:
            # test message
            await self.get_channel(1234117670996148246).send(
                f"Server {server.name} kicked the bot"
            )


intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
client = WordChainClient(intents=intents, command_prefix="/")


@client.tree.command(name="myscore")
async def myscore(ctx: discord.Interaction):
    result, data = db.get_score(ctx.guild.id, ctx.user.id)
    if not result:
        await ctx.response.send_message(data)
        return
    id, score, rank = data
    message = f"```\n{rank}. {ctx.user.display_name} {score}\n```"
    await ctx.response.send_message(message)


@client.tree.command(name="score")
async def score(ctx: discord.Interaction):
    result, data = db.leaderboard(ctx.guild.id)
    if not result:
        await ctx.response.send_message(data)
        return

    message = "```\n"
    for user_row in data:
        rank, id, score = user_row
        user = await client.fetch_user(id)
        message += f"{rank}. {user.display_name} {score}\n"
    message += "```"
    await ctx.response.send_message(message)


@client.tree.command(name="meaning")
@app_commands.describe(word="Find the meaning of this word")
async def meaning(ctx: discord.Interaction, word: str):
    if word.isalpha():
        response = requests.get(
            f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
        )
        if response.status_code == 400:
            await ctx.response.send_message("Meaning of this word not found")
        try:
            meaning = response.json()[0]["meanings"][0]["definitions"][0]["definition"]
            await ctx.response.send_message(f"`{word}: {meaning}`")
        except:
            await ctx.response.send_message(
                f"Sorry pal! No meaning found for **{word}**. It could be a proper noun."
            )
        return
    await ctx.response.send_message("Invalid word")


@client.tree.command(name="help")
async def help(ctx: discord.Interaction):
    await ctx.response.send_message(
        """
Wordchain Rules
**1**. Check the previous accepted word.
**2**. Using the last letter of that write a new word.
**3**. NO CONSECUTIVE TURNS ALLOWED.
**4**. 7 or more characters in the word = 6 points.
**5**. 6 or lesser characters in the word = 4 points.
**6**. Same starting and ending letter = Additional 2 points.
**7**. Out of turn, wrong word in the chain = **2 points will be deducted**.
**8**. Word length has to be greater than 3.
Commands
```
/myscore
/score
/meaning <word>
```
"""
    )
