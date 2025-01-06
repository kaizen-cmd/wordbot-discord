from scripts.send_custom_message import send_embed_to_server
import datetime
from logging_config import get_logger
from elements import GamingRefreeEmbed

logger = get_logger(__name__)


class Insights:

    def __init__(self, db):
        self.server_rank_map = dict()
        self.db = db

        # 2 days, 3 days, 4 days
        self.intervals = [172800, 259200, 345600]
        self.interval_index = 0
        self.last_run = datetime.datetime.now()
        self.refresh_cache()

    def refresh_cache(self):
        self.server_rank_map = {
            server_id: (rank, server_id, coins)
            for rank, server_id, coins in self.db.get_top_servers(limit=15)[1]
        }

    def compare_cache_and_send_messages(self):
        current_top_servers = self.db.get_top_servers(limit=10)[1]

        for i, server in enumerate(current_top_servers, start=1):
            message = ""
            current_rank, server_id, current_coins = server
            prev_rank, _server_id, prev_coins = self.server_rank_map.get(
                server_id, (0, 0, 0)
            )

            if _server_id == 0:
                continue

            if current_rank > prev_rank:
                message = f"🚨 Oh no! Your server dropped from **#{prev_rank}** to **#{current_rank}**. Run `/top_servers` to check the leaderboard now and rally your team to climb back up!"

            elif current_rank < prev_rank:

                if current_rank > 2 and current_rank < 5 and i != 1:
                    coins_to_top = current_top_servers[0][2] - current_coins
                    message = f"🔥 Your server is just **{coins_to_top}** 💰 coins away from taking the #1 spot! Rally your players and run `/top_servers` to see your progress!"

                elif current_top_servers[i - 1][2] - current_coins < 200 and i != 1:
                    coins_to_next_spot = current_top_servers[i - 1][2] - current_coins
                    message = f"🔥 Your server is just **{coins_to_next_spot}** 💰 coins away from taking the #{i} spot! Rally your players and run `/top_servers` to see your progress!"

                else:
                    message = f"🎉 Congratulations! Your server climbed from **#{prev_rank}** to **#{current_rank}**. Run `/top_servers` to check the leaderboard now and keep the momentum going!"

            else:
                message = f"👀 Your server is currently at **#{current_rank}**. The competition is heating up! Encourage everyone to participate and run `/top_servers` to track progress!"

            embed = GamingRefreeEmbed(
                title="Server Rank Update",
                description=message,
            )
            send_embed_to_server(embed.to_dict(), server_id)

        self.server_rank_map = {
            server_id: (rank, server_id, coins)
            for rank, server_id, coins in current_top_servers
        }

    def send(self):

        elapsed_time = (datetime.datetime.now() - self.last_run).total_seconds()
        current_interval = self.intervals[self.interval_index]

        if elapsed_time >= current_interval:
            logger.info("Sending insights")
            self.compare_cache_and_send_messages()

            self.last_run = datetime.datetime.now()
            self.interval_index = (self.interval_index + 1) % len(self.intervals)
