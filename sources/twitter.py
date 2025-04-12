#!/usr/bin/env python3
print("Script is starting execution...")

import os
import time
from datetime import datetime, timezone, timedelta
import tweepy
from dotenv import load_dotenv
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from helpers import is_today
from supabase_client import SupabaseClient

# Load environment variables
load_dotenv()

# Initialize Supabase client
supabase = SupabaseClient()

# Set Twitter bearer token from environment
BEARER_TOKEN = os.getenv('TWITTER_BEARER_TOKEN')
print("🔑 Twitter Bearer Token:", BEARER_TOKEN[:10] + "..." + BEARER_TOKEN[-10:])

# Initialize Twitter client
client = tweepy.Client(bearer_token=BEARER_TOKEN)
print("🤖 Twitter client initialized")

def handle_rate_limit(attempt: int = 1):
    """Handle rate limit with exponential backoff.
    
    Args:
        attempt: The current attempt number (default: 1)
    """
    wait_time = min(900 * (1.5 ** (attempt - 1)), 3600)  # Max 1 hour wait
    print(f"Rate limit hit. Waiting for {wait_time/60:.1f} minutes...")
    time.sleep(wait_time)

def fetch_tweets_for_user(client, username):
    """Fetch tweets for a specific user."""
    max_retries = 3
    retry_count = 0
    base_delay = 5  # Base delay between requests in seconds
    
    while retry_count < max_retries:
        try:
            print(f"\n🔍 Fetching tweets for user: {username} (Attempt {retry_count + 1}/{max_retries})")
            
            # Add increasing delay between requests
            delay = base_delay * (retry_count + 1)
            print(f"⏳ Waiting {delay} seconds before request...")
            time.sleep(delay)
            
            # Get user ID from username
            print(f"🔑 Looking up user ID for @{username}...")
            user = client.get_user(username=username)
            if not user.data:
                print(f"❌ User @{username} not found")
                return []
            
            print(f"✅ Found user ID: {user.data.id}")
            
            # Calculate time range (last 24 hours)
            now = datetime.now(timezone.utc)
            start_time = now - timedelta(hours=24)
            start_time_str = start_time.strftime('%Y-%m-%dT%H:%M:%SZ')
            
            print(f"📅 Fetching tweets since: {start_time_str}")
            print(f"⏰ Current time: {now.strftime('%Y-%m-%dT%H:%M:%SZ')}")
            
            # Add delay between requests
            time.sleep(base_delay)
            
            # Fetch user's tweets using their ID
            print(f"📥 Fetching tweets for user ID {user.data.id}...")
            tweets = client.get_users_tweets(
                id=user.data.id,
                start_time=start_time_str,
                tweet_fields=["created_at", "id", "text", "referenced_tweets", "public_metrics"],
                expansions=["referenced_tweets.id"],
                max_results=10
            )
            
            if not tweets.data:
                print(f"ℹ️ No tweets found for @{username} in the last 24 hours")
                return []
            
            print(f"✅ Found {len(tweets.data)} tweets for @{username}")
            # Format tweets
            formatted_tweets = []
            for tweet in tweets.data:
                # Check if this is a retweet
                is_retweet = False
                retweeted_username = None
                if tweet.referenced_tweets:
                    for ref in tweet.referenced_tweets:
                        if ref.type == "retweeted":
                            is_retweet = True
                            # Get the retweeted tweet's author
                            retweeted_tweet = next((t for t in tweets.includes.get('tweets', []) 
                                                  if t.id == ref.id), None)
                            if retweeted_tweet:
                                retweeted_username = retweeted_tweet.author_id
                            break
                
                # Get engagement metrics
                metrics = tweet.public_metrics if hasattr(tweet, 'public_metrics') else {}
                
                tweet_url = f"https://twitter.com/{username}/status/{tweet.id}"
                formatted_tweets.append({
                    "company": username,
                    "author": username,
                    "content": tweet.text,
                    "timestamp": tweet.created_at.isoformat(),
                    "source": "twitter",
                    "tweet_url": tweet_url,
                    "is_retweet": is_retweet,
                    "retweeted_author": retweeted_username,
                    "like_count": metrics.get('like_count', 0),
                    "retweet_count": metrics.get('retweet_count', 0),
                    "reply_count": metrics.get('reply_count', 0),
                    "quote_count": metrics.get('quote_count', 0)
                })
                print(f"📝 Processed tweet: {tweet.id} (Retweet: {is_retweet})")
                print(f"📊 Engagement: {metrics.get('like_count', 0)} likes, {metrics.get('retweet_count', 0)} retweets")
            
            return formatted_tweets
            
        except tweepy.TooManyRequests:
            print(f"⚠️ Rate limit hit on attempt {retry_count + 1}")
            if retry_count < max_retries - 1:
                handle_rate_limit(retry_count + 1)
                retry_count += 1
            else:
                print(f"❌ Failed to fetch tweets for @{username} after {max_retries} attempts")
                return []
        except Exception as e:
            print(f"❌ Error fetching tweets for @{username}: {str(e)}")
            retry_count += 1
            if retry_count < max_retries:
                time.sleep(base_delay * retry_count)  # Exponential backoff for other errors
            else:
                return []
    
    return []

def save_tweet_to_supabase(tweet_data):
    """Save a tweet to the Supabase messages table."""
    try:
        # Check if tweet already exists
        if supabase.is_tweet_exists(tweet_data["author"], tweet_data["content"]):
            print(f"⏭️ Tweet from {tweet_data['author']} already exists, skipping...")
            return None

        # Save tweet to database
        response = supabase.client.table("messages").insert(tweet_data).execute()
        
        if response.data:
            print(f"✅ Saved tweet from {tweet_data['author']}")
            return response.data
        else:
            print(f"❌ Failed to save tweet from {tweet_data['author']}")
            return None
    except Exception as e:
        print(f"❌ Error saving tweet from {tweet_data['author']}: {e}")
        return None

def fetch_today_tweets(usernames):
    """Fetch today's tweets for a list of usernames."""
    print("🚀 Starting Twitter fetch for macro handles...")
    print(f"📊 Will fetch tweets from {len(usernames)} handles: {', '.join(usernames)}")
    
    # Calculate today's midnight in CET
    now = datetime.now(timezone.utc)
    cet_offset = timedelta(hours=1)  # CET is UTC+1
    cet_time = now + cet_offset
    start_time = datetime(cet_time.year, cet_time.month, cet_time.day, 0, 0, 0, tzinfo=timezone.utc) - cet_offset
    print(f"📅 Fetching tweets since: {start_time.isoformat()} (CET midnight)")
    
    all_tweets = []
    for username in usernames:
        tweets = fetch_tweets_for_user(client, username)
        for tweet in tweets:
            # Save tweet to Supabase
            save_tweet_to_supabase(tweet)
        all_tweets.extend(tweets)
    
    print(f"\n✅ Successfully fetched {len(all_tweets)} tweets:")
    for tweet in all_tweets:
        print(f"\n@{tweet['author']}:")
        print(f"📝 {tweet['content']}")
        print(f"⏰ {tweet['timestamp']}")
        print(f"🔗 {tweet['tweet_url']}")
    
    return all_tweets

# List of macro-focused Twitter handles to track
MACRO_HANDLES = [
    "qthomp",
    "RaoulGMI",
    "fejau_inc",
    "DariusDale42",
    "CavanXy",
    "Citrini7",
    "FedGuy12",
    "fundstrat",
    "dgt10011",
    "Bluntz_Capital",
    "AriDavidPaul",
    "cburniske"
]

if __name__ == "__main__":
    print("🚀 Starting Twitter fetch for macro handles...")
    print(f"📊 Will fetch tweets from {len(MACRO_HANDLES)} handles: {', '.join(MACRO_HANDLES)}")
    
    tweets = fetch_today_tweets(MACRO_HANDLES)
    
    if tweets:
        print(f"\n✅ Successfully fetched {len(tweets)} tweets:")
        for tweet in tweets:
            print(f"\n@{tweet['author']}:")
            print(f"📝 {tweet['content']}")
            print(f"⏰ {tweet['timestamp']}")
            print(f"🔗 {tweet['tweet_url']}")
    else:
        print("\n❌ No tweets found for today.") 