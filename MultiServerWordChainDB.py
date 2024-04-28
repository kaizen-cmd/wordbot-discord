import sqlite3
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


class MultiServerWordChainDB:

    def __init__(self):
        self.server_table_mapping = defaultdict(list)
        self.conn = sqlite3.connect("db.sqlite3")
        self.curr = self.conn.cursor()
        self.negative_marks = 2
        self.marks_for_word_length_gte_seven = 6
        self.marks_for_word_length_lte_seven = 4
        self.marks_for_same_start_end_word = 2

        # Populate server_table_mapping with existing tables in the database
        self.curr.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing_tables = self.curr.fetchall()
        for table_name in existing_tables:
            table_name = table_name[0]  # Extract table name from tuple
            server_id = "_".join(table_name.split("_")[0:-1])
            self.server_table_mapping[server_id].append(table_name)

    def get_users_table_name(self, server_id):
        return f"users_{server_id}"

    def get_words_table_name(self, server_id):
        return f"words_{server_id}"

    def get_last_char_user_table_name(self, server_id):
        return f"lcu_{server_id}"

    def is_server_onboard(self, server_id):
        user_table = self.get_users_table_name(server_id)
        status = self.curr.execute(
            f"SELECT name FROM sqlite_master WHERE type='table' AND name='{user_table}'"
        ).fetchone()
        return bool(status)

    def onboard_server(self, server_id):

        user_table = self.get_users_table_name(server_id)
        word_table = self.get_words_table_name(server_id)
        last_char_user_table = self.get_last_char_user_table_name(server_id)

        self.curr.execute(
            f"CREATE TABLE IF NOT EXISTS {word_table}(word text primary key, isUsed integer default 0)"
        )
        self.curr.execute(
            f"CREATE TABLE IF NOT EXISTS {user_table}(id integer primary key, score integer default 0)"
        )

        self.curr.execute(
            f"CREATE TABLE IF NOT EXISTS {last_char_user_table}(last_char varchar(1) default '', last_user_id integer default 0, id integer default 1 primary key)"
        )
        self.curr.execute(f"INSERT INTO {last_char_user_table} (id) values(1)")
        self.conn.commit()

        self.server_table_mapping[server_id].append(
            (user_table, word_table, last_char_user_table)
        )

        with open("words_alpha.txt", "r") as f:
            words = list()
            for word in f.readlines():
                word = word.strip().lower()
                if len(word) >= 3:
                    words.append((word,))
            self.curr.executemany(f"INSERT INTO {word_table} (word) VALUES (?)", words)
            self.conn.commit()

    def try_play_word(self, server_id, player_id, word):

        user_table = self.get_users_table_name(server_id)
        word_table = self.get_words_table_name(server_id)
        last_char_user_table = self.get_last_char_user_table_name(server_id)

        user_score = self.curr.execute(
            f"SELECT score FROM {user_table} WHERE id=?", (player_id,)
        ).fetchone()

        if not user_score:
            self.curr.execute(
                f"INSERT INTO {user_table} (id) VALUES (?)",
                (player_id,),
            )
            self.conn.commit()
            logger.info(f"User added ID: {player_id} Server ID: {server_id}")
            user_score = 0
        else:
            user_score = user_score[0]

        last_char, last_user_id = self.curr.execute(
            f"SELECT last_char, last_user_id FROM {last_char_user_table} WHERE id=1"
        ).fetchone()

        if player_id == last_user_id:
            user_score = max(0, user_score - self.negative_marks)
            self.curr.execute(
                f"UPDATE {user_table} SET score=? WHERE id=?", (user_score, player_id)
            )
            self.conn.commit()
            return (
                False,
                f"It is not your turn. **{self.negative_marks} points deducted**",
            )

        if last_char and word[0] != last_char:
            user_score = max(0, user_score - self.negative_marks)
            self.curr.execute(
                f"UPDATE {user_table} SET score=? WHERE id=?", (user_score, player_id)
            )
            self.conn.commit()
            return (
                False,
                f"Word's first character does not match the last character. **{self.negative_marks} points deducted**",
            )

        word_result = self.curr.execute(
            f"SELECT word, isUsed FROM {word_table} WHERE word=?", (word,)
        ).fetchone()

        if not word_result:
            return (False, "Word does not exist in the dictionary")

        word_in_db, is_word_used = word_result

        if is_word_used:
            return (False, "Word already used")

        if len(word) > 7:
            user_score += self.marks_for_word_length_gte_seven
        else:
            user_score += self.marks_for_word_length_lte_seven

        if word[0] == word[-1]:
            user_score += self.marks_for_same_start_end_word

        self.curr.execute(
            f"UPDATE {user_table} SET score=? WHERE id=?", (user_score, player_id)
        )
        self.curr.execute(f"UPDATE {word_table} SET isUsed=1 WHERE word=?", (word,))
        self.curr.execute(
            f"UPDATE {last_char_user_table} SET last_user_id=?, last_char=? WHERE id=1",
            (player_id, word[-1]),
        )
        self.conn.commit()
        next_word_exists = self.curr.execute(
            f"SELECT word FROM {word_table} WHERE isUsed=0 AND word LIKE '{word[-1]}%' LIMIT 1"
        ).fetchone()
        if not next_word_exists:
            for i in "abcdefghijklmnopqrstuvwxyz":
                next_word_exists = self.curr.execute(
                    f"SELECT word FROM {word_table} WHERE isUsed=0 AND word LIKE '{i}%' LIMIT 1"
                ).fetchone()
                if next_word_exists:
                    return (True, i)

        return (True, "Word accepted")

    def get_score(self, server_id, player_id):
        user_table = self.get_users_table_name(server_id)

        QUERY = f"SELECT id, score, (SELECT COUNT(DISTINCT score) + 1 FROM {user_table} WHERE score > u.score) AS rank FROM {user_table} u WHERE id = {player_id}"
        result = self.curr.execute(QUERY).fetchone()
        if not result:
            return (False, "Start playing")
        id, score, rank = result
        return (True, (id, score, rank))

    def leaderboard(self, server_id):
        user_table = self.get_users_table_name(server_id)
        QUERY = f"SELECT id, score FROM {user_table} ORDER BY score DESC LIMIT 10"
        user_rows = self.curr.execute(QUERY).fetchall()
        if not user_rows:
            return (False, "Start playing")

        result = []
        for rank, user_row in enumerate(user_rows, start=1):
            id, score = user_row
            result.append((rank, id, score))
        return (True, result)
