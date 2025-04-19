import os
import requests
import time
import logging
from flask import Flask
from threading import Thread
from dotenv import load_dotenv

# === Load environment variables ===
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TWITTER_BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN")

# === Twitter usernames to track ===
TWITTER_USERNAMES = [
    "WatcherGuru", "CoinDesk", "Cointelegraph", "CryptoSlate"
]

# === Keywords to filter tweets ===
KEYWORDS = ["crypto", "just in", "alert", "breaking", "update"]

# === Polling interval (seconds) ===
CHECK_INTERVAL = 60

# === Flask keep-alive server ===
app = Flask('')

@app.route('/')
def home():
    return "I'm alive!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# === Twitter API setup ===
twitter_headers = {
    'Authorization': f'Bearer {TWITTER_BEARER_TOKEN}'
}

# Track last tweet IDs to avoid duplicates
last_tweet_ids = {}

# === Get user ID from Twitter username ===
def get_user_id(username):
    url = f"https://api.twitter.com/2/users/by/username/{username}"
    response = requests.get(url, headers=twitter_headers)
    if response.status_code == 200:
        return response.json()['data']['id']
    else:
        logging.warning(f"Failed to get user ID for {username}")
        return None

# === Get latest tweets from user ===
def get_latest_tweet(user_id):
    url = f"https://api.twitter.com/2/users/{user_id}/tweets?max_results=5&tweet.fields=created_at"
    response = requests.get(url, headers=twitter_headers)
    if response.status_code == 200:
        return response.json().get('data', [])
    else:
        logging.warning(f"Failed to fetch tweets for user_id {user_id}")
        return []

# === Send message to Telegram ===
def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }
    requests.post(url, data=payload)

# === Main bot logic ===
def start_bot():
    user_ids = {}

    # Get Twitter user IDs
    for username in TWITTER_USERNAMES:
        user_id = get_user_id(username)
        if user_id:
            user_ids[username] = user_id
            last_tweet_ids[user_id] = None

    print("Bot started successfully. Monitoring tweets...")

    while True:
        for username, user_id in user_ids.items():
            tweets = get_latest_tweet(user_id)
            for tweet in tweets:
                tweet_id = tweet['id']
                text = tweet['text'].lower()
                if last_tweet_ids[user_id] != tweet_id:
                    if any(keyword.lower() in text for keyword in KEYWORDS):
                        msg = f"<b>{username}</b> tweeted:\n\n{text}\n\nhttps://twitter.com/{username}/status/{tweet_id}"
                        send_telegram_message(msg)
                        print(f"Sent alert for {username}: {tweet_id}")
                    last_tweet_ids[user_id] = tweet_id
        time.sleep(CHECK_INTERVAL)

# === Run everything ===
if __name__ == "main":
    keep_alive()
    start_bot()