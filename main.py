import sqlite3
import discord
import os

CHANNEL_ID = 1225453961751035974


class WordGameDB:
    def __init__(self, db_file="database.sqlite3"):
        self.db_file = db_file
        self.conn = sqlite3.connect(db_file)
        self.curr = self.conn.cursor()

    def create_tables(self):
        self.curr.execute(
            "CREATE TABLE IF NOT EXISTS words(word text primary key, isUsed integer default 0)"
        )
        self.curr.execute("CREATE INDEX IF NOT EXISTS isUsed_index ON words(isUsed)")
        self.curr.execute(
            "CREATE TABLE IF NOT EXISTS users(id integer primary key, username text, servername text, score integer default 0)"
        )
        self.curr.execute(
            "CREATE TABLE IF NOT EXISTS last_char(lastchar varchar(1) default '', last_user_id integer default 0, id integer default 1 primary key)"
        )
        self.curr.execute("INSERT INTO last_char(id) values(1)")
        self.conn.commit()

    def load_words(self, file_path="words_alpha.txt"):
        with open(file_path, "r") as f:
            words = list()
            for word in f.readlines():
                word = word.strip()
                if len(word) >= 2:
                    words.append((word, ))
            self.curr.executemany("INSERT INTO words (word) VALUES (?)", words)
            self.conn.commit()

    def update_score(self, user, points):
        score = self.curr.execute(
            f"SELECT score FROM users WHERE id=?", (user.id,)
        ).fetchone()
        if not score:
            self.curr.execute(
                "INSERT INTO users(id, username, servername) VALUES (?, ?, ?)",
                (user.id, user.name, user.display_name),
            )
            self.conn.commit()
            score = (0,)
        score = score[0] + points
        self.curr.execute("UPDATE users SET score=? WHERE id=?", (score, user.id))
        self.conn.commit()
        return score

    def try_play_word(self, word, user):
        lastchar = self.curr.execute(
            "SELECT lastchar FROM last_char WHERE id=1"
        ).fetchone()[0]
        last_user = self.curr.execute(
            "SELECT last_user_id FROM last_char WHERE id=1"
        ).fetchone()[0]
        db_word = self.curr.execute(
            "SELECT word, isUsed FROM words WHERE word=?", (word,)
        ).fetchone()

        if not db_word:
            return "WND"  # Word not in the dictionary
        elif lastchar and word[0] != lastchar:
            return "WFCNM"  # Word's first character does not match the last character
        elif db_word[1] == 1:
            return "WAU"  # Word is already used
        elif last_user != 0 and user.id == last_user:
            return "NYT"  # Not this user's turn
        else:
            self.curr.execute("UPDATE words SET isUsed=1 WHERE word=?", (word,))
            self.curr.execute("UPDATE last_char SET lastchar=? WHERE id=1", (word[-1],))
            self.curr.execute(
                "UPDATE last_char SET last_user_id=? WHERE id=1", (user.id,)
            )
            self.conn.commit()
            return "WA"  # Accept word


class WordGameClient(discord.Client):
    def __init__(self, db, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.db = db

    async def on_ready(self):
        print(f"We have logged in as {self.user}")

    def validate_message(self, message):
        if message.author == self.user or message.channel.id != CHANNEL_ID:
            return False
        try:
            message = int("message")
            return False
        except:
            words = message.split(" ")
            if len(words) > 1:
                return False
            word = words[0]
            return word.isalpha()

    async def on_message(self, message: discord.message.Message):
        if self.validate_message(message.content):
            message = message.lower()
            result = self.db.try_play_word(message, message.author)
            if result == "WA":
                score = self.db.update_score(message.author, len(message))
                await message.add_reaction("✅")
                await message.channel.send(
                    content=f"+{len(message.content)} points! {message.author.display_name}'s score {score}"
                )
            elif result == "NYT":
                await message.channel.send("Not your turn")
            elif result == "WAU":
                await message.add_reaction("❌")
                await message.channel.send("Word already used")
            elif result == "WND":
                await message.add_reaction("❌")
                await message.channel.send("Word not in the dictionary")
            elif result == "WFCNM":
                await message.add_reaction("❌")
                await message.channel.send(
                    "Check the last character of the previous word"
                )


if __name__ == "__main__":
    db = WordGameDB()
    # db.create_tables()
    # db.load_words()

    token = os.getenv(
        "TOKEN",
        "MTIyNTQ5MDc1OTQzMjc5ODMyMA.GBK0hM.7cIV6gluTopYAOsmtbYD0hkvmgChVAeYTWJDdg",
    )
    intents = discord.Intents.default()
    intents.messages = True
    intents.message_content = True
    client = WordGameClient(db, intents=intents)
    client.run(token)
