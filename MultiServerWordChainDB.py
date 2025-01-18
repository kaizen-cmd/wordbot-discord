import datetime
import random
import sqlite3
from collections import namedtuple
from typing import Tuple

from logging_config import get_logger

logger = get_logger(__name__)


class MultiServerWordChainDB:

    def __init__(self):
        self.conn = sqlite3.connect("db.sqlite3")
        self.curr = self.conn.cursor()
        self.negative_marks = 2
        self.marks_for_word_length_gte_seven = 6
        self.marks_for_word_length_lte_seven = 4
        self.marks_for_same_start_end_word = 2
        self.char_list = list("abcdefghijklmnopqrstuvwxyz")
        self._create_voting_record_table()
        self._create_words_refresh_table()
        self._alter_users_table_for_streak_and_last_played()
        self._alter_users_table_for_streak_bonus_message_sent_column()

    def __del__(self):
        self.curr.close()
        self.conn.close()

    def get_words_table_name(self, server_id):
        return f"words_{server_id}"

    def is_server_onboard(self, server_id):
        word_table = self.get_words_table_name(server_id)
        status = self.curr.execute(
            f"SELECT name FROM sqlite_master WHERE type='table' AND name='{word_table}'"
        ).fetchone()
        return bool(status)

    def onboard_server(self, server_id):

        word_table = self.get_words_table_name(server_id)

        self.curr.execute(
            f"CREATE TABLE IF NOT EXISTS {word_table}(word text primary key, isUsed integer default 0)"
        )
        self.curr.execute(
            f"CREATE TABLE IF NOT EXISTS users(id integer primary key, user_id varchar(255), score integer default 0, server_id varchar(255))"
        )

        self.curr.execute(
            f"INSERT INTO lu(last_char, last_user_id, server_id) VALUES('', 0, '{server_id}')"
        )
        self.conn.commit()

        with open("words_alpha.txt", "r") as f:
            words = list()
            for word in f.readlines():
                word = word.strip().lower()
                if len(word) >= 3:
                    words.append((word,))
            self.curr.executemany(f"INSERT INTO {word_table} (word) VALUES (?)", words)
            self.conn.commit()

        logger.info(f"On boarded server {server_id}")

    def deboard_server(self, server_id):
        word_table = self.get_words_table_name(server_id)

        self.curr.execute(f"DROP TABLE {word_table}")
        self.curr.execute(f"DELETE FROM users WHERE server_id='{server_id}'")
        self.curr.execute(f"DELETE FROM lu WHERE server_id='{server_id}'")
        self.conn.commit()
        logger.info(f"De boarded server {server_id}")

    def try_play_word(self, server_id, player_id, word):

        word_table = self.get_words_table_name(server_id)

        user_score = self.curr.execute(
            f"SELECT score FROM users WHERE user_id=? AND server_id=?",
            (
                str(player_id),
                str(server_id),
            ),
        ).fetchone()

        if not user_score:
            self.curr.execute(
                f"INSERT INTO users (user_id, server_id) VALUES (?, ?) ",
                (str(player_id), str(server_id)),
            )
            self.conn.commit()
            logger.info(f"User added ID: {player_id} Server ID: {server_id}")
            user_score = 0
        else:
            user_score = user_score[0]

        last_char, last_user_id = self.curr.execute(
            f"SELECT last_char, last_user_id FROM lu WHERE server_id='{server_id}'"
        ).fetchone()

        if player_id == last_user_id:
            user_score = max(0, user_score - self.negative_marks)
            self.curr.execute(
                f"UPDATE users SET score=? WHERE user_id=? AND server_id=?",
                (user_score, str(player_id), str(server_id)),
            )
            self.conn.commit()
            return (
                False,
                f"It is not your turn. **{self.negative_marks} coins 💰 deducted**",
                self.negative_marks,
            )

        if last_char and word[0] != last_char:
            user_score = max(0, user_score - self.negative_marks)
            self.curr.execute(
                f"UPDATE users SET score=? WHERE user_id=? AND server_id=?",
                (user_score, str(player_id), str(server_id)),
            )
            self.conn.commit()
            return (
                False,
                f"Write a word starting with {last_char}. **{self.negative_marks} coins 💰 deducted**",
                self.negative_marks,
            )

        word_result = self.curr.execute(
            f"SELECT word, isUsed FROM {word_table} WHERE word=?", (word,)
        ).fetchone()

        if not word_result:
            return (
                False,
                "Word does not exist in the dictionary",
                0,
            )

        word_in_db, is_word_used = word_result

        if is_word_used:
            return (False, "Word already used", 0)

        voting_record = self.curr.execute(
            f"SELECT word_count FROM voting_records WHERE user_id='{player_id}'"
        ).fetchone()
        points_obtained = 0
        if len(word) >= 7:
            points_obtained += self.marks_for_word_length_gte_seven
        else:
            points_obtained += self.marks_for_word_length_lte_seven

        if word[0] == word[-1]:
            points_obtained += self.marks_for_same_start_end_word

        if voting_record and voting_record[0] > 0 and points_obtained > 0:
            points_obtained += points_obtained
            self.curr.execute(
                f"UPDATE voting_records SET word_count={voting_record[0] - 1} WHERE user_id='{player_id}'"
            )
            self.conn.commit()

        user_score += points_obtained

        self.curr.execute(
            f"UPDATE users SET score=? WHERE user_id=? AND server_id=?",
            (user_score, str(player_id), str(server_id)),
        )
        self.curr.execute(f"UPDATE {word_table} SET isUsed=1 WHERE word=?", (word,))
        self.curr.execute(
            f"UPDATE lu SET last_user_id=?, last_char=? WHERE server_id='{server_id}'",
            (player_id, word[-1]),
        )
        self.conn.commit()
        next_word_exists = self.curr.execute(
            f"SELECT word FROM {word_table} WHERE isUsed=0 AND word LIKE '{word[-1]}%' LIMIT 1"
        ).fetchone()

        if not next_word_exists:
            return (
                True,
                self._change_letter(server_id=server_id),
                points_obtained,
            )

        return (
            True,
            "Word accepted",
            points_obtained,
        )

    def update_user_streak(self, server_id, player_id) -> Tuple[int, str]:
        streak, message = -1, ""
        self.curr.execute(
            "SELECT last_played, streak, streak_bonus_message_sent FROM users WHERE user_id=? AND server_id=?",
            (player_id, server_id),
        )

        user_row = self.curr.fetchone()

        if not user_row or not user_row[0]:
            message = "New streak started"
            self.curr.execute(
                "UPDATE users SET streak=1, last_played=datetime('now') WHERE user_id=? AND server_id=?",
                (player_id, server_id),
            )
            self.conn.commit()
            return 1, message

        streak = user_row[1]
        last_played = datetime.datetime.strptime(user_row[0], "%Y-%m-%d %H:%M:%S")
        time_now = datetime.datetime.now()

        if time_now >= last_played + datetime.timedelta(
            days=1
        ) and time_now < last_played + datetime.timedelta(days=2):
            self.curr.execute(
                "UPDATE users SET streak=streak+1, last_played=datetime('now') WHERE user_id=? AND server_id=?",
                (player_id, server_id),
            )
            self.conn.commit()
            streak += 1
            message = f"🔥Streak achieved for **{streak}** days🔥"

        elif time_now >= last_played + datetime.timedelta(days=2):
            self.curr.execute(
                "UPDATE users SET streak=1, last_played=datetime('now') WHERE user_id=? AND server_id=?",
                (player_id, server_id),
            )
            self.conn.commit()
            streak = 1
            message = "Streak broken. Starting a new streak."

        streak_bonus_period = 20
        if streak and streak % streak_bonus_period == 0 and not user_row[2] == streak:
            multiplier = streak // streak_bonus_period
            coins = min(300, multiplier * streak_bonus_period)
            message += f" 🎉🎉🎉 **20 days !!** 🎉🎉🎉 You recieve additional **{coins}** coins 💰 for maintaining the streak"
            self.curr.execute(
                "UPDATE users SET score=score+?, streak_bonus_message_sent=? WHERE user_id=? AND server_id=?",
                (coins, streak, player_id, server_id),
            )
            self.conn.commit()
        return streak, message

    def get_score(self, server_id, player_id):

        QUERY = f"SELECT user_id, score, (SELECT COUNT(DISTINCT score) + 1 FROM users WHERE score > u.score AND server_id='{server_id}') AS rank FROM users u WHERE user_id = '{player_id}' AND server_id='{server_id}'"
        result = self.curr.execute(QUERY).fetchone()
        if not result:
            return (False, "Ask them to start playing")
        id, score, rank = result
        return (True, (id, score, rank))

    def get_streak_count(self, server_id, player_id):
        self.curr.execute(
            "SELECT streak FROM users WHERE user_id=? AND server_id=?",
            (player_id, server_id),
        )
        streak = self.curr.fetchone()[0]
        return streak

    def leaderboard(self, server_id):
        QUERY = f"SELECT user_id, score FROM users WHERE server_id='{server_id}' ORDER BY score DESC LIMIT 5"
        user_rows = self.curr.execute(QUERY).fetchall()
        if not user_rows:
            return (False, "Start playing")

        result = []
        for rank, user_row in enumerate(user_rows, start=1):
            id, score = user_row
            result.append((rank, id, score))
        return (True, result)

    def get_global_leaderboard(self):
        QUERY = (
            f"SELECT user_id, score, server_id FROM users ORDER BY score DESC LIMIT 5"
        )
        user_rows = self.curr.execute(QUERY).fetchall()
        if not user_rows:
            return (False, "Start playing")

        result = []
        for rank, user_row in enumerate(user_rows, start=1):
            id, score, server_id = user_row
            result.append((rank, id, score, server_id))
        return (True, result)

    def create_or_update_voting_record(self, user_id: str, word_count: int):
        voting_record = self.curr.execute(
            f"SELECT user_id, word_count FROM voting_records WHERE user_id='{user_id}'"
        ).fetchone()
        if not voting_record:
            self.curr.execute(
                f"INSERT INTO voting_records VALUES('{user_id}', {word_count})"
            )
            voting_record = self.curr.execute(
                f"SELECT word_count FROM voting_records WHERE user_id='{user_id}'"
            ).fetchone()
        else:
            self.curr.execute(
                f"UPDATE voting_records SET word_count={voting_record[1] + word_count} WHERE user_id='{user_id}'"
            )
            voting_record = self.curr.execute(
                f"SELECT word_count FROM voting_records WHERE user_id='{user_id}'"
            ).fetchone()
        self.conn.commit()
        VotingRecord = namedtuple("voting_record", ["user_id", "word_count"])
        return VotingRecord(voting_record[0], voting_record[1])

    def refresh_words(self, server_id):
        last_refresh = self.curr.execute(
            f"SELECT timestamp FROM words_refresh WHERE server_id='{server_id}'"
        ).fetchone()

        if last_refresh:
            last_refresh = datetime.datetime.strptime(
                last_refresh[0], "%Y-%m-%d %H:%M:%S"
            )

        if (
            not last_refresh
            or last_refresh < datetime.datetime.now() - datetime.timedelta(days=21)
        ):
            logger.info(f"[WORD REFRESH] Refreshing words for server {server_id}")
            self.curr.execute(
                f"INSERT INTO words_refresh VALUES(datetime('now'), '{server_id}')"
            )
            self.conn.commit()
            word_table = self.get_words_table_name(server_id)
            for letter in "abcdefghijklmnopqrstuvwxyz":
                self.curr.execute(
                    f"SELECT COUNT(word) FROM {word_table} WHERE word LIKE '{letter}%' AND isUsed=1"
                )
                used_words = self.curr.fetchone()[0]
                limit = int(used_words * 0.25)
                if letter in ("x", "z", "y"):
                    limit = int(used_words * 0.4)
                self.curr.execute(
                    f"UPDATE {word_table} SET isUsed=0 WHERE word LIKE '{letter}%' AND isUsed=1 ORDER BY RANDOM() LIMIT {limit}"
                )
            self.conn.commit()

    def get_top_servers(self, limit=5):
        QUERY = f"SELECT server_id, SUM(score) FROM users GROUP BY server_id ORDER BY SUM(score) DESC LIMIT {limit}"
        self.curr.execute(QUERY)
        server_rows = self.curr.fetchall()
        if not server_rows:
            return (False, "No server data available")
        result = []
        for rank, server_row in enumerate(server_rows, start=1):
            id, score = server_row
            result.append((rank, id, score))
        return (True, result)

    def _change_letter(self, server_id):

        word_table = self.get_words_table_name(server_id)

        random.shuffle(self.char_list)
        for i in self.char_list:
            next_word_exists = self.curr.execute(
                f"SELECT word FROM {word_table} WHERE isUsed=0 AND word LIKE '{i}%' LIMIT 1"
            ).fetchone()
            if next_word_exists:
                self.curr.execute(
                    f"UPDATE lu SET last_char=? WHERE server_id='{server_id}'",
                    (i),
                )
                self.conn.commit()
                return i

    def _create_voting_record_table(self):
        self.curr.execute(
            "CREATE TABLE IF NOT EXISTS voting_records(user_id VARCHAR(255), word_count INTEGER)"
        )

    def _create_words_refresh_table(self):
        self.curr.execute(
            "CREATE TABLE IF NOT EXISTS words_refresh(timestamp TIMESTAMP, server_id VARCHAR(255))"
        )

    def _alter_users_table_for_streak_and_last_played(self):
        try:
            self.curr.execute("SELECT streak FROM users")
        except sqlite3.OperationalError:
            self.curr.execute("ALTER TABLE users ADD COLUMN streak INTEGER DEFAULT 0")
            self.conn.commit()

        try:
            self.curr.execute("SELECT last_played FROM users")
        except sqlite3.OperationalError:
            self.curr.execute("ALTER TABLE users ADD COLUMN last_played TIMESTAMP ")
            self.conn.commit()

    def _alter_users_table_for_streak_bonus_message_sent_column(self):
        try:
            self.curr.execute("SELECT streak_bonus_message_sent FROM users")
        except sqlite3.OperationalError:
            self.curr.execute(
                "ALTER TABLE users ADD COLUMN streak_bonus_message_sent INTEGER DEFAULT 0"
            )
            self.conn.commit()
