import discord
from discord.ui import View


class VoteButtonsView(discord.ui.View):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @discord.ui.button(style=discord.ButtonStyle.green, label="Vote for 2x coins #1")
    async def send_vote_btn(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.send_message(
            "Vote on https://top.gg/bot/1225490759432798320 to get double coins 💰 on next 5 accepted words"
        )

    @discord.ui.button(style=discord.ButtonStyle.red, label="Vote for 2x coins #2")
    async def send_discordbotlist_vote_btn(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.send_message(
            "Vote on https://discordbotlist.com/bots/gamingrefree to get double coins 💰 on next 5 accepted words"
        )


class GamingRefreeEmbed(discord.Embed):

    def __init__(self, *args, **kwargs):
        image_url = None
        if "image_url" in kwargs:
            image_url = kwargs.pop("image_url")
        super().__init__(*args, **kwargs)
        self.set_image(url=image_url)
        self.url = "https://gamingrefree.online"
        self.colour = 0x1EEB36
        self.set_footer(
            text="Made by GamingRefree Inc.", icon_url="https://i.imgur.com/O5rRjUu.png"
        )
        self.set_author(
            name="GamingRefree",
            url="https://gamingrefree.online",
            icon_url="https://i.imgur.com/O5rRjUu.png",
        )
