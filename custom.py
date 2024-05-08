import sqlite3

conn = sqlite3.connect("db.sqlite3")
curr = conn.cursor()
curr.execute(
    "UPDATE words_1234116258186657872 SET isUsed=1 WHERE word LIKE 'y%'"
).fetchone()
conn.commit()
curr.close()
conn.close()
