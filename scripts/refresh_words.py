import logging
import sqlite3
import time

logger = logging.getLogger(__name__)

logger.info("REFRESHING WORDS !")

conn = sqlite3.connect("../db.sqlite3")
curr = conn.cursor()

word_tables = [
    table[0]
    for table in curr.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name LIKE 'words_%'"
    ).fetchall()
]

curr.close()
conn.close()

logger.info(f"{len(word_tables)} word tables found")
word_count = 0

start_letters = "abcdefghijklmnopqrstuvwxyz"
for word_table in word_tables:
    conn = sqlite3.connect("../db.sqlite3")
    curr = conn.cursor()
    for letter in start_letters:
        words = curr.execute(
            f"SELECT word FROM {word_table} WHERE isUsed = 1 AND word LIKE ? ORDER BY RANDOM() LIMIT 5",
            (f"{letter}%",),
        ).fetchall()
        if words:
            word_list = [word[0] for word in words]
            word_count += len(word_list)
            placeholders = ", ".join("?" for _ in word_list)
            curr.execute(
                f"UPDATE {word_table} SET isUsed = 0 WHERE word IN ({placeholders})",
                word_list,
            )
    conn.commit()
    curr.close()
    conn.close()
    time.sleep(100)

logger.info(f"{word_count} words refreshed")
