import os
import time
import re
import requests
import feedparser
from datetime import datetime

RSS_URL = "https://www.regjeringen.no/api/rss?types=officialfromcouncil&langs=no"
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL")
SLEEP_INTERVAL = 10  # Endret til å sjekke hvert 10. sekund mellom 11:00 og 12:00

seen_entries = set()

def check_feed_and_notify():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Sjekker feed...")
    try:
        feed = feedparser.parse(RSS_URL)
        if feed.bozo:
            print(f"Feil ved parsing: {feed.bozo_exception}")
            return

        for entry in feed.entries:
            entry_id = entry.get("id", entry.link)
            if entry_id not in seen_entries:
                print(f"Fant ny sak fra statsråd: {entry.title}")
                send_to_slack(entry.title, entry.link, entry.get("description", ""))
                seen_entries.add(entry_id)
    except Exception as e:
        print(f"Uventet feil: {e}")

def send_to_slack(title, link, description):
    clean_description = re.sub('<[^<]+?>', '', description)
    if len(clean_description) > 300:
        clean_description = clean_description[:297] + "..."

    slack_data = {
        "blocks": [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "🚨 Nytt fra Statsråd!"}
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{title}*\n{clean_description}\n\n<{link}|Les hele saken her>"
                }
            }
        ]
    }
    try:
        res = requests.post(SLACK_WEBHOOK_URL, json=slack_data)
        if res.status_code == 200:
            print("Sendt til Slack!")
    except Exception as e:
        print(f"Feil ved sending til Slack: {e}")

if __name__ == "__main__":
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starter overvåking...")
    
    # Laster inn eksisterende saker kl. 11:00 slik at kun *nye* saker utover timen blir varslet
    initial_feed = feedparser.parse(RSS_URL)
    for entry in initial_feed.entries:
        seen_entries.add(entry.get("id", entry.link))
    print(f"Registrerte {len(seen_entries)} eksisterende saker. Overvåker til kl. 12:00 med {SLEEP_INTERVAL} sekunders intervall...")

    # Kjører så lenge timen er 11 (frem til 12:00:00)
    while datetime.now().hour == 11:
        check_feed_and_notify()
        time.sleep(SLEEP_INTERVAL)

    print("Klokken er 12:00. Avslutter kjøring.")
