import logging
import os

from WordChainClient import construct_client
from dotenv import load_dotenv

import datetime

import discord

if ".env" not in os.listdir():
    raise Exception(".env not found")

load_dotenv(".env")

logging.basicConfig(
    filename="app.log",
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger("app")


class App:

    TOKEN = ""
    CLIENT = construct_client()

    def __init__(self, token) -> None:
        App.TOKEN = token

    def add_slash_commands(self):
        @App.CLIENT.tree.command(
            name="global_leaderboard", description="get global leaders in wordchain"
        )
        async def global_leaderboard(interaction: discord.Interaction):
            with open("global_ranks.txt", "r+") as f:
                lines = f.readlines()
                if len(
                    lines
                ) == 0 or datetime.datetime.now() > datetime.datetime.strptime(
                    lines[0].strip(), "%d/%m/%Y, %H:%M:%S"
                ) + datetime.timedelta(
                    hours=4
                ):
                    ranks = list()
                    for server_id in list(App.CLIENT.server_channel_mapping.keys()):
                        exists, result = App.CLIENT.db.leaderboard(server_id)
                        if exists:
                            for rec in result:
                                server_rank, id, score = rec
                                ranks.append((id, score))
                    ranks.sort(key=lambda x: x[1])

                    with open("global_ranks.txt", "w") as f2:
                        f2.write(datetime.datetime.now().strftime("%d/%m/%Y, %H:%M:%S"))
                        f2.write("\n")
                        for i in range(min(len(ranks), 5)):
                            user = await App.CLIENT.fetch_user(ranks[i][0])
                            f2.write(
                                f"{ user.global_name},{ranks[i][1]},{user.avatar.url}"
                            )
                            f2.write("\n")
            embed = discord.Embed(title="Global leaderboard (Updates every 4 hours)")
            embed.color = discord.Color.brand_green()
            with open("global_ranks.txt", "r") as f:
                lines = f.readlines()
                rank = 1
                for i in lines[1:]:
                    username, points, avatar = i.split(",")
                    if not embed.thumbnail.url:
                        embed.set_thumbnail(url=avatar)
                    embed.add_field(
                        value=f"#{rank}.    @{username}    {points} points",
                        name="",
                        inline=False,
                    )
                    rank += 1
            await interaction.response.send_message(embed=embed)

    def run(self):
        App.CLIENT.run(App.TOKEN)


if __name__ == "__main__":
    app = App(os.getenv("BOT_TOKEN"))
    app.add_slash_commands()
    logger.info("Started Wordchain instance")
    app.run()
