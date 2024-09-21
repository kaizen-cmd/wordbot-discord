import logging
import random
import sqlite3
from collections import defaultdict, namedtuple

logger = logging.getLogger(__name__)


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
            )

        word_result = self.curr.execute(
            f"SELECT word, isUsed FROM {word_table} WHERE word=?", (word,)
        ).fetchone()

        if not word_result:
            return (False, "Word does not exist in the dictionary")

        word_in_db, is_word_used = word_result

        if is_word_used:
            return (False, "Word already used")

        voting_record = self.curr.execute(
            f"SELECT word_count FROM voting_records WHERE user_id='{player_id}'"
        ).fetchone()
        points_obtained = 0
        if len(word) > 7:
            user_score += self.marks_for_word_length_gte_seven
            points_obtained += self.marks_for_word_length_gte_seven
        else:
            user_score += self.marks_for_word_length_lte_seven
            points_obtained += self.marks_for_word_length_lte_seven

        if word[0] == word[-1]:
            user_score += self.marks_for_same_start_end_word
            points_obtained += self.marks_for_same_start_end_word

        if voting_record and voting_record[0] > 0 and points_obtained > 0:
            user_score += points_obtained
            self.curr.execute(
                f"UPDATE voting_records SET word_count={voting_record[0] - 1} WHERE user_id='{player_id}'"
            )
            self.conn.commit()

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
            return (True, self._change_letter(server_id=server_id))

        return (True, "Word accepted")

    def get_score(self, server_id, player_id):

        QUERY = f"SELECT user_id, score, (SELECT COUNT(DISTINCT score) + 1 FROM users WHERE score > u.score) AS rank FROM users u WHERE user_id = '{player_id}' AND server_id='{server_id}'"
        result = self.curr.execute(QUERY).fetchone()
        if not result:
            return (False, "Ask them to start playing")
        id, score, rank = result
        return (True, (id, score, rank))

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
        QUERY = f"SELECT user_id, score FROM users ORDER BY score DESC LIMIT 5"
        user_rows = self.curr.execute(QUERY).fetchall()
        if not user_rows:
            return (False, "Start playing")

        result = []
        for rank, user_row in enumerate(user_rows, start=1):
            id, score = user_row
            result.append((rank, id, score))
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
