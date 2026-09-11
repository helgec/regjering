import os
import time
import re
import requests
import feedparser
from datetime import datetime

RSS_URL = "https://www.regjeringen.no/api/rss?types=officialfromcouncil&langs=no"
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL")
SLEEP_INTERVAL = 10  # Sekunder mellom hver sjekk

seen_entries = set()

def fetch_feed():
    """Henter feeden via requests med en User-Agent for å unngå blokkering."""
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    response = requests.get(RSS_URL, headers=headers, timeout=10)
    response.raise_for_status()
    return feedparser.parse(response.content)

def check_feed_and_notify():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Sjekker feed...")
    try:
        feed = fetch_feed()
        
        # Hvis feeden mangler saker helt på grunn av en feil, avbryter vi
        if not feed.entries and feed.bozo:
            print(f"Parsefeil (ingen saker funnet): {feed.bozo_exception}")
            return

        for entry in feed.entries:
            entry_id = entry.get("id", entry.link)
            if entry_id not in seen_entries:
                print(f"Fant ny sak fra statsråd: {entry.title}")
                send_to_slack(entry.title, entry.link, entry.get("description", ""))
                seen_entries.add(entry_id)

    except Exception as e:
        print(f"Uventet feil ved sjekk av feed: {e}")

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
        else:
            print(f"Feil fra Slack API: {res.status_code}")
    except Exception as e:
        print(f"Feil ved sending til Slack: {e}")

if __name__ == "__main__":
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starter overvåking...")
    
    # Laster inn eksisterende saker ved oppstart
    try:
        initial_feed = fetch_feed()
        for entry in initial_feed.entries:
            seen_entries.add(entry.get("id", entry.link))
        print(f"Registrerte {len(seen_entries)} eksisterende saker. Overvåker til kl. 12:00 med {SLEEP_INTERVAL} sekunders intervall...")
    except Exception as e:
        print(f"Kunne ikke laste inn startdata: {e}")

    # Kjører så lenge timen er 11 (frem til kl. 12:00)
    while datetime.now().hour == 11:
        check_feed_and_notify()
        time.sleep(SLEEP_INTERVAL)

    print("Klokken er 12:00. Avslutter kjøring.")
