import os
import time
import re
import requests
import feedparser

# RSS-feed spesifikt for "Offisielt fra statsråd"
RSS_URL = "https://www.regjeringen.no/api/rss?types=officialfromcouncil&langs=no"
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL")
SLEEP_INTERVAL = 15  # Sekunder mellom hver sjekk

seen_entries = set()

def check_feed_and_notify():
    print(f"Sjekker feed: {RSS_URL}...")
    try:
        feed = feedparser.parse(RSS_URL)
        
        if feed.bozo:
            print(f"Feil ved parsing av feed: {feed.bozo_exception}")
            return

        # Går gjennom alle nye meldinger om Offisielt fra statsråd
        for entry in feed.entries:
            entry_id = entry.get("id", entry.link)
            
            # Hvis vi allerede har behandlet denne, hopp over
            if entry_id in seen_entries:
                continue
                
            title = entry.title
            description = entry.get("description", "")
            link = entry.link
            
            print(f"Fant ny sak fra statsråd: {title}")
            send_to_slack(title, link, description)
                
            # Marker som sett
            seen_entries.add(entry_id)
            
    except Exception as e:
        print(f"En uventet feil oppstod under sjekk av feed: {e}")

def send_to_slack(title, link, description):
    """Sender melding til Slack via Webhook."""
    clean_description = re.sub('<[^<]+?>', '', description)
    if len(clean_description) > 300:
        clean_description = clean_description[:297] + "..."

    slack_data = {
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "🚨 Nytt fra Statsråd!"
                }
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
        response = requests.post(SLACK_WEBHOOK_URL, json=slack_data)
        if response.status_code != 200:
            print(f"Feil ved sending til Slack: {response.status_code}, {response.text}")
        else:
            print("Melding sendt til Slack!")
    except Exception as e:
        print(f"Nettverksfeil ved sending til Slack: {e}")

if __name__ == "__main__":
    print("Starter overvåking av Offisielt fra statsråd...")
    
    # Fyller settet ved oppstart for å unngå å sende gamle meldinger på nytt
    initial_feed = feedparser.parse(RSS_URL)
    for entry in initial_feed.entries:
        seen_entries.add(entry.get("id", entry.link))
    print(f"Lastet inn {len(seen_entries)} eksisterende saker. Venter på nye...")
    
    while True:
        time.sleep(SLEEP_INTERVAL)
        check_feed_and_notify()
