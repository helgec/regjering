import os
import time
import feedparser
import requests

# Konfigurasjon
RSS_URL = "https://www.regjeringen.no/api/rss?types=news&langs=no" # Standard RSS for nyheter på regjeringen.no
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL")
SLEEP_INTERVAL = 30 # Sekunder mellom hver sjekk

# Søkeordene vi ser etter (gjort til små bokstaver for enklere matching)
KEYWORDS = ["kong harald", "gravferd", "begravelse"]

# Vi bruker et Set for å lagre ID-ene til nyhetene vi allerede har sett og sendt, 
# slik at vi unngår å sende samme melding til Slack flere ganger.
seen_entries = set()

def check_feed_and_notify():
    print(f"Sjekker feed: {RSS_URL}...")
    try:
        feed = feedparser.parse(RSS_URL)
        
        # Sjekker om feeden ble hentet riktig
        if feed.bozo:
            print(f"Feil ved parsing av feed: {feed.bozo_exception}")
            return

        # Går gjennom alle elementene (nyhetene) i feeden
        for entry in feed.entries:
            entry_id = entry.get("id", entry.link)
            
            # Hvis vi allerede har behandlet denne, hopp over
            if entry_id in seen_entries:
                continue
                
            title = entry.title
            description = entry.get("description", "")
            link = entry.link
            
            # Kombinerer tittel og beskrivelse, og gjør alt til små bokstaver for søket
            content_to_check = (title + " " + description).lower()
            
            # Sjekk om noen av søkeordene finnes i teksten
            if any(keyword in content_to_check for keyword in KEYWORDS):
                print(f"Fant relevant nyhet: {title}")
                send_to_slack(title, link, description)
                
            # Marker som sett, uansett om den var relevant eller ikke
            # (så vi ikke sjekker den samme uaktuelle nyheten om og om igjen)
            seen_entries.add(entry_id)
            
    except Exception as e:
        print(f"En uventet feil oppstod under sjekk av feed: {e}")

def send_to_slack(title, link, description):
    """Sender en formatert melding til Slack via Webhook."""
    
    # Renser ut HTML-tags hvis det finnes i beskrivelsen
    import re
    clean_description = re.sub('<[^<]+?>', '', description)
    
    # Korter ned beskrivelsen hvis den er for lang
    if len(clean_description) > 300:
        clean_description = clean_description[:297] + "..."

    slack_data = {
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "🚨 Ny relevant pressemelding fra Regjeringen!"
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
    print("Starter overvåking av regjeringen.no...")
    
    # Første kjøring: Populer seen_entries uten å sende varsler
    # Dette hindrer at scriptet sender 50 Slack-meldinger første gang du starter det
    initial_feed = feedparser.parse(RSS_URL)
    for entry in initial_feed.entries:
         seen_entries.add(entry.get("id", entry.link))
    print(f"Lastet inn {len(seen_entries)} eksisterende nyheter. Venter på nye...")
    
    # Hovedløkken som kjører hvert 30. sekund
    while True:
        check_feed_and_notify()
        time.sleep(SLEEP_INTERVAL)
