import discord


class VoteButton(discord.ui.View):

    def __init__(self, *args, **kwargs):
        super().__init__()

    @discord.ui.button(style=discord.ButtonStyle.green, label="Vote for 2x coins")
    async def send_vote_btn(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.send_message(
            "Vote on https://top.gg/bot/1225490759432798320 to get double coins 💰 on next 5 accepted words"
        )
