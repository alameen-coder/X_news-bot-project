import os
import requests
import time
import logging

from flask import Flask
from threading import Thread

# === KEEP_ALIVE SERVER ===
app = Flask('')

@app.route('/')
def home():
   return "Im alive!"

def run():
    app.run(host='0.0.0.0', port=8080)  

def keep_alive():
        t = Thread(target=run)
        t.start()
       


from dotenv import load_dotenv
load_dotenv()


TELEGRAM_BOT_TOKEN = "7709846260:AAGtFq9brzDFA3obIDx1WMVEvrtOuDx3RRU"
TELEGRAM_CHAT_ID = "6224709482"  

TWITTER_BEARER_TOKEN = "AAAAAAAAAAAAAAAAAAAAAOax0gEAAAAADPPWBv8h9yDlOGTfKJDAiELE%2FEk%3D32GWLsSpcsO2tno6XtT6I1XR5YRenxzKVp1VzGYs6zdBkLvoX1"
TWITTER_USERNAMES = ["@WatcherGuru", "@CoinDesk", "@Cointelegraph", "@CryptoSlate", "@arkham"]                             
KEYWORDS = ["Crypto, just in" ]                           
CHECK_INTERVAL = 60  # Time interval in seconds to check for new tweets

# === HEADERS ===
twitter_headers = {
    'Authorization': f'Bearer {TWITTER_BEARER_TOKEN}'
}

# === STATE ===
last_seen = {}

# === LOGGING ===
logging.basicConfig(level=logging.INFO)

# === FUNCTIONS ===
def get_user_id(usernname): 
    try: 
        url = f"https://api.twitter.com/2/users/by/username/{usernname}"
        response = requests.get(url, headers=twitter_headers)
        response.raise_for_status()
        return response.json()['data']['id']
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching user ID for {usernname}: {e}")
        return None
    
    def get_latest_tweets(user_id):
        try: 
            url = f"https://api.twitter.com/2/users/{user_id}/tweets?max_results=5&exclude=replies"
            params = {
                'max_results': 5,  # Adjust as needed
                'tweet.fields': 'created_at,text'
            }
            response = requests.get(url, headers=twitter_headers, params=params)
            response.raise_for_status()
            tweets = response.json().get('data', [])
            return tweets[0] if tweets else None
        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching tweets for user ID {user_id}: {e}")
            return None
        
    def contains_keywords(text):
        return any(keyword.lower() in text.lower() for keyword in KEYWORDS)
    
    def send_to_telegram(message):
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            payload = {
                'chat_id': TELEGRAM_CHAT_ID,
                'text': message,
                'parse_mode': 'HTML'
            }
            response = requests.post(url, json=payload)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            logging.error(f"Error sending message to Telegram: {e}")

            def format_message(tweet):
                tweet_url = f"https://twitter.com/{tweet['author_id']}/status/{tweet['id']}"
                text = tweet['text'].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                return f"<b>New Tweet from @{tweet['author_id']}:</b>\n\n{text}\n\n<a href='{tweet_url}'>View on Twitter</a>"
            
            # === MAIN LOOP ===
            if __name__ == "__main__":
                user_ids = {u: get_user_id(u) for u in TWITTER_USERNAMES}
                logging.info("Bot started successfully.")

                while true: 
                    for username, user_id in user_ids.items():
                        if not user_id: 
                            continue
                        twee_latest_tweets(user_id)
                        if tweet: 
                            tweet_id = tweet['id']
                            if last_seen.get(usernname) != tweet_id: 
                                if contains_keywords (tweet['text']): 
                                    message = format_message(usernname, tweet)
                                    send_to_telegram(message)
                                    logging.info(f"New tweet from @{username}")
                                    last_seen[username] = tweet_id
                                    time.sleep(CHECK_INTERVAL)
