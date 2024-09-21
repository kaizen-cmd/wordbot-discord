import sqlite3

conn = sqlite3.connect("db.sqlite3")
curr = conn.cursor()

curr.execute(
    f"CREATE TABLE IF NOT EXISTS lu(last_char varchar(1) default '', last_user_id integer default 0, id integer default 1 primary key, server_id varchar(255))"
)

curr.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'lcu_%'")
existing_tables = curr.fetchall()
for table in existing_tables:

    table_name = table[0]

    server_id = table_name.split("_")[1]

    curr.execute(f"SELECT last_char, last_user_id FROM {table_name}")
    last_char, last_user_id = curr.fetchone()
    curr.execute(
        f"INSERT INTO lu(last_char, last_user_id, server_id) VALUES('{last_char}', '{last_user_id}', '{server_id}')"
    )

for table in existing_tables:

    table_name = table[0]
    curr.execute(f"DROP TABLE {table_name}")

conn.commit()
