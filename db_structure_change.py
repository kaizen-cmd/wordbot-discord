import sqlite3

conn = sqlite3.connect("db.sqlite3")
curr = conn.cursor()

# curr.execute("DROP TABLE users")

curr.execute(
    f"CREATE TABLE IF NOT EXISTS users(id integer primary key, user_id varchar(255), score integer default 0, server_id varchar(255))"
)

curr.execute(
    "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'users_%'"
)
existing_tables = curr.fetchall()
for table in existing_tables:

    table_name = table[0]

    server_id = table_name.split("_")[1]

    curr.execute(f"SELECT id, score FROM {table_name}")
    res = curr.fetchall()
    for user_id, score in res:
        curr.execute(
            f"INSERT INTO users(user_id, score, server_id) VALUES('{user_id}', '{score}', '{server_id}')"
        )

conn.commit()
