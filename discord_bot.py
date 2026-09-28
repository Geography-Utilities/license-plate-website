import requests
from dotenv import load_dotenv
load_dotenv()

import os

BOT_TOKEN = os.environ.get("DISCORD_BOT_TOKEN")
CHANNEL_ID = os.environ.get("DISCORD_CHANNEL_ID")

def send_message(submission_id, text, channel_id=CHANNEL_ID):
    resp = requests.post(
        f"https://discord.com/api/v10/channels/{channel_id}/messages",
        headers={
            "Authorization": f"Bot {BOT_TOKEN}",
            "User-Agent": "DiscordBot (https://github.com/Geography-Utilities/license-plate-website, 1.0.0)"
        },
        json={
            "content": f"{text}\n[View](https://plates.geoutils.us/submissions/{submission_id})"
        },
        timeout=5,
    )
    resp.raise_for_status()
    return int(resp.json()["id"])


if __name__ == "__main__":
    send_message(submission_id=1, text="New Submission to Approve or Deny")