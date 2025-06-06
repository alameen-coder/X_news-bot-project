import os
import requests
import time
import logging
import re
from flask import Flask
from threading import Thread
from dotenv import load_dotenv
import json

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
KEYWORDS = [ "crypto", "just in", "alert", "breaking", "update", "bitcoin", "ethereum",
    "solana", "xrp", "bnb", "sui",
    "altcoin", "blockchain", "news", "market", "trading", "analysis", "report",
    "bullish", "bearish", "bull", "bear", "dip", "pump", "dump", "moon",
    "dump", "hodl", "FOMO", "FUD", "FOMO", "FUD", "bull run", "bear market",
    "bull trap"]

# Compile regex pattern for keywords with word boundaries for precise matching
KEYWORD_PATTERN = re.compile(r'\b(' + '|'.join(re.escape(k) for k in KEYWORDS) + r')\b', re.IGNORECASE)

# === Polling interval (seconds) ===
CHECK_INTERVAL = 60

# === Flask keep-alive server ===
app = Flask('')

@app.route('/')
def home():
    return "I'm alive!"

def run():
    app.run(host='0.0.0.0', port=5500)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()

# === Twitter API setup ===
twitter_headers = {
    'Authorization': f'Bearer {TWITTER_BEARER_TOKEN}'
}

# Track last tweet IDs to avoid duplicates
last_tweet_ids = {}

# === Get user ID from Twitter username ===
def get_user_id(username):
    try:
        url = f"https://api.twitter.com/2/users/by/username/{username}"
        response = requests.get(url, headers=twitter_headers, timeout=10)
        if response.status_code == 429:
            logging.warning(f"Rate limit hit while getting user ID for {username}.")
            return None
        response.raise_for_status()
        return response.json()['data']['id']
    except Exception as e:
        logging.warning(f"Failed to get user ID for {username}: {e}")
        return None

# === Get latest tweets from user with 429 handling ===
def get_latest_tweet(user_id, max_retries=3):
    retry_delay = 60  # seconds
    retries = 0
    while retries <= max_retries:
        try:
            url = f"https://api.twitter.com/2/users/{user_id}/tweets?max_results=5&tweet.fields=created_at"
            response = requests.get(url, headers=twitter_headers, timeout=10)
            if response.status_code == 429:
                logging.warning(f"Rate limit hit for user_id {user_id}. Retrying after {retry_delay} seconds.")
                time.sleep(retry_delay)
                retries += 1
                retry_delay *= 2  # exponential backoff
                continue
            response.raise_for_status()
            return response.json().get('data', [])
        except Exception as e:
            logging.warning(f"Failed to fetch tweets for user_id {user_id}: {e}")
            return []
    logging.warning(f"Max retries exceeded for user_id {user_id}. Skipping.")
    return []

# === Send message to Telegram ===
def send_telegram_message(text, chat_id=TELEGRAM_CHAT_ID, reply_markup=None):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML"
        }
        if reply_markup:
            payload["reply_markup"] = json.dumps(reply_markup)
        response = requests.post(url, data=payload, timeout=10)
        response.raise_for_status()
    except Exception as e:
        logging.warning(f"Failed to send Telegram message: {e}")

# === Send photo to Telegram by uploading local file ===
def send_telegram_photo_file(photo_path, caption, chat_id=TELEGRAM_CHAT_ID):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
        with open(photo_path, "rb") as photo_file:
            files = {"photo": photo_file}
            data = {
                "chat_id": chat_id,
                "caption": caption,
                "parse_mode": "HTML"
            }
            response = requests.post(url, files=files, data=data, timeout=10)
            response.raise_for_status()
    except Exception as e:
        logging.warning(f"Failed to send Telegram photo by file: {e}")

# === Send welcome message ===
def send_welcome_message(chat_id):
    welcome_msg = "Welcome to the X News Bot! I will notify you about all important crypto news for you to stay positioned."
    photo_path = "welcome.jpg"  # Replace with your local image file path if needed
    # Send photo first, ignore errors
    try:
        send_telegram_photo_file(photo_path, welcome_msg, chat_id)
    except Exception as e:
        logging.warning(f"Failed to send welcome photo: {e}")
    # Send welcome text message without any keyboard or buttons
    send_telegram_message(welcome_msg, chat_id, reply_markup=None)

# === Telegram bot polling to handle commands ===
def telegram_polling():
    offset = None
    while True:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
            params = {"timeout": 100, "offset": offset}
            response = requests.get(url, params=params, timeout=110)
            response.raise_for_status()
            updates = response.json().get("result", [])
            for update in updates:
                offset = update["update_id"] + 1
                if "message" in update:
                    message = update["message"]
                    chat_id = message["chat"]["id"]
                    text = message.get("text", "").strip().lower()
                    if text == "/start":
                        send_welcome_message(chat_id)
                    # Additional command handling can be added here
        except Exception as e:
            logging.warning(f"Error in telegram_polling: {e}")
            time.sleep(5)
        time.sleep(1)

# === Main bot logic ===
def start_bot():
    user_ids = {}

    # Get Twitter user IDs
    for username in TWITTER_USERNAMES:
        user_id = get_user_id(username)
        if user_id:
            user_ids[username] = user_id
            last_tweet_ids[user_id] = None
        else:
            logging.warning(f"Skipping username {username} due to missing user ID.")

    print("Bot started successfully. Monitoring tweets...")

    # Start Telegram polling in a separate thread
    telegram_thread = Thread(target=telegram_polling)
    telegram_thread.daemon = True
    telegram_thread.start()

    while True:
        for username, user_id in user_ids.items():
            tweets = get_latest_tweet(user_id)
            # Find the latest tweet containing any keyword
            latest_matching_tweet = None
            for tweet in tweets:
                text = tweet['text']
                if KEYWORD_PATTERN.search(text):
                    if (latest_matching_tweet is None) or (tweet['id'] > latest_matching_tweet['id']):
                        latest_matching_tweet = tweet
            if latest_matching_tweet:
                tweet_id = latest_matching_tweet['id']
                if last_tweet_ids[user_id] != tweet_id:
                    msg = f"<b>{username}</b> tweeted:\n\n{latest_matching_tweet['text']}\n\nhttps://twitter.com/{username}/status/{tweet_id}"
                    send_telegram_message(msg)
                    print(f"Sent alert for {username}: {tweet_id}")
                    last_tweet_ids[user_id] = tweet_id
            time.sleep(1)  # small delay between user requests to reduce rate limit hits
        time.sleep(CHECK_INTERVAL)

# === Run everything ===
if __name__ == "__main__":
    keep_alive()
    # Note: Consider persisting last_tweet_ids to avoid missing tweets on restart
    start_bot()
