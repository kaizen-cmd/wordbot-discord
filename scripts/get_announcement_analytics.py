import json
import requests
import os

headers = {
    "Authorization": f'Bot {os.getenv("BOT_TOKEN")}',
    "Content-Type": "application/json",
}


def get_analytics():
    sent_embeds = {}
    with open("sent_ids.json", "r") as f:
        sent_embeds = json.loads(f.read())

    for title in sent_embeds:
        print(f"Title: {title}")
        print(f"Sent to {len(sent_embeds[title])} servers")
        # get reactions count
        total_reactions = 0
        total_replies = 0
        for channel_id, message_id in sent_embeds[title]:
            response = requests.get(
                f"https://discord.com/api/v9/channels/{channel_id}/messages/{message_id}",
                headers=headers,
            )
            if response.status_code == 200:
                json_response = response.json()
                total_reactions += sum(
                    [r["count"] for r in (json_response.get("reactions") or [])]
                )
                total_replies += len(json_response.get("message_reference") or [])

        return {
            "title": title,
            "sent_to": len(sent_embeds[title]),
            "total_reactions": total_reactions,
            "total_replies": total_replies,
        }


print(get_analytics())
