"""
Usage: python3 exhaust_words_cli.py --letter <letter> --server_id <server_id>
"""

import sqlite3
import argparse


def exhaust_words_beginning_with(letter, server_id):
    conn = sqlite3.connect("db.sqlite3")
    curr = conn.cursor()
    curr.execute(
        f"UPDATE words_{server_id} SET isUsed=1 WHERE word LIKE '{letter}%'"
    ).fetchone()
    conn.commit()
    curr.close()
    conn.close()


def main():
    parser = argparse.ArgumentParser(
        description="CLI to exhaust words beginning with a given letter for a specific server."
    )
    parser.add_argument(
        "--letter", required=True, help="The starting letter of the words to exhaust."
    )
    parser.add_argument(
        "--server_id", required=True, type=int, help="The ID of the server."
    )
    args = parser.parse_args()

    letter = args.letter.lower()
    server_id = args.server_id

    exhaust_words_beginning_with(letter, server_id)
    print(f"Words beginning with '{letter}' exhausted for server ID {server_id}.")


if __name__ == "__main__":
    main()
