#!/usr/bin/env python3
print("Script is starting execution...")

import os
import warnings
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
import tweepy
import time
import asyncio
from typing import List, Dict, Optional, Set
import sys
import json
from collections import defaultdict
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from supabase_client import SupabaseClient

# Filter out all syntax warnings from tweepy
warnings.filterwarnings("ignore", category=SyntaxWarning)

# Load environment variables
load_dotenv()

# Initialize Supabase client
supabase = SupabaseClient()

# Initialize cache for user IDs to reduce API calls
user_id_cache = {}
tweet_cache = {}

def is_today(date: datetime) -> bool:
    """Check if a date is from today."""
    today = datetime.now(timezone.utc).date()
    return date.date() == today

# List of Twitter handles to monitor
MACRO_HANDLES = [
    "fejau_inc",
    "DariusDale42",
    "CavanXy",
    "Citrini7",
    "FedGuy12",
    "fundstrat",
    "dgt10011",
    "Bluntz_Capital",
    "AriDavidPaul",
    "cburniske",
    "qthomp",
    "RaoulGMI"
]

def initialize_twitter_client() -> tweepy.Client:
    """Initialize the Twitter API client."""
    bearer_token = os.getenv("TWITTER_BEARER_TOKEN")
    if not bearer_token:
        raise ValueError("TWITTER_BEARER_TOKEN environment variable is not set")
        
    print(f"🔑 Twitter Bearer Token: {bearer_token[:10]}...{bearer_token[-10:]}")
    client = tweepy.Client(bearer_token=bearer_token, wait_on_rate_limit=True)
    print("🤖 Twitter client initialized")
    return client

# Rate limiter class
class RateLimiter:
    def __init__(self, max_requests: int, time_window: int):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = []
        
    async def wait_if_needed(self):
        now = time.time()
        
        # Remove old requests
        self.requests = [req_time for req_time in self.requests if now - req_time < self.time_window]
        
        if len(self.requests) >= self.max_requests:
            # Wait until oldest request expires
            sleep_time = self.time_window - (now - self.requests[0])
            if sleep_time > 0:
                print(f"⏳ Rate limit reached. Waiting {sleep_time:.0f} seconds...")
                await asyncio.sleep(sleep_time)
                
        self.requests.append(now)

# Initialize rate limiter (3 requests per 15 minutes)
rate_limiter = RateLimiter(max_requests=3, time_window=900)

async def get_user_id(client: tweepy.Client, username: str) -> Optional[str]:
    """Get user ID with caching."""
    if username in user_id_cache:
        return user_id_cache[username]
        
    try:
        user = client.get_user(username=username)
        if not user.data:
            print(f"❌ User @{username} not found")
            return None
            
        user_id = user.data.id
        user_id_cache[username] = user_id
        return user_id
        
    except Exception as e:
        print(f"❌ Error getting user ID for @{username}: {str(e)}")
        return None

async def fetch_tweets_for_user(username: str, client: tweepy.Client) -> List[Dict]:
    """Fetch tweets for a specific user from the last 24 hours using batch processing."""
    try:
        # Get user ID
        user_id = await get_user_id(client, username)
        if not user_id:
            return []
            
        # Calculate time range for last 24 hours
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=24)
        
        # Try to fetch tweets with improved retry mechanism
        max_retries = 3
        retry_count = 0
        wait_time = 30
        
        while retry_count < max_retries:
            try:
                # Fetch tweets excluding retweets and replies
                tweets = client.get_users_tweets(
                    id=user_id,
                    start_time=start_time,
                    end_time=end_time,
                    exclude=["retweets", "replies"],
                    tweet_fields=["created_at", "public_metrics", "entities", "conversation_id", "author_id"],
                    expansions=["referenced_tweets.id"],
                    max_results=100
                )
                
                if not tweets.data:
                    print(f"ℹ️ No tweets found for @{username}")
                    return []
                
                # Process tweets and handle threads
                processed_tweets = []
                conversation_tweets = defaultdict(list)
                
                # First pass: collect all tweets and group by conversation
                for tweet in tweets.data:
                    if is_today(tweet.created_at):
                        tweet_data = {
                            "id": tweet.id,
                            "content": tweet.text,
                            "author": username,
                            "timestamp": tweet.created_at.isoformat(),
                            "tweet_url": f"https://twitter.com/{username}/status/{tweet.id}",
                            "public_metrics": {
                                "like_count": tweet.public_metrics["like_count"],
                                "retweet_count": tweet.public_metrics["retweet_count"],
                                "reply_count": tweet.public_metrics["reply_count"],
                                "quote_count": tweet.public_metrics["quote_count"]
                            },
                            "conversation_id": tweet.conversation_id,
                            "author_id": tweet.author_id
                        }
                        
                        # If this is part of a conversation, add to the conversation group
                        if tweet.conversation_id != tweet.id:
                            conversation_tweets[tweet.conversation_id].append(tweet_data)
                        else:
                            processed_tweets.append(tweet_data)
                
                # Second pass: handle conversations and referenced tweets
                for conversation_id, thread_tweets in conversation_tweets.items():
                    # Sort tweets by timestamp
                    thread_tweets.sort(key=lambda x: x["timestamp"])
                    
                    # Combine thread tweets into a single entry
                    combined_content = "\n\n".join([f"@{t['author']}: {t['content']}" for t in thread_tweets])
                    combined_metrics = {
                        "like_count": sum(t["public_metrics"]["like_count"] for t in thread_tweets),
                        "retweet_count": sum(t["public_metrics"]["retweet_count"] for t in thread_tweets),
                        "reply_count": sum(t["public_metrics"]["reply_count"] for t in thread_tweets),
                        "quote_count": sum(t["public_metrics"]["quote_count"] for t in thread_tweets)
                    }
                    
                    processed_tweets.append({
                        "id": conversation_id,
                        "content": combined_content,
                        "author": username,
                        "timestamp": thread_tweets[0]["timestamp"],
                        "tweet_url": f"https://twitter.com/{username}/status/{conversation_id}",
                        "public_metrics": combined_metrics,
                        "is_thread": True,
                        "thread_length": len(thread_tweets)
                    })
                
                return processed_tweets
                
            except tweepy.TooManyRequests as e:
                retry_count += 1
                if retry_count < max_retries:
                    print(f"⚠️ Rate limit hit for @{username}. Retry {retry_count}/{max_retries} in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                    wait_time *= 2
                else:
                    print(f"❌ Max retries reached for @{username}. Skipping...")
                    return []
                    
            except tweepy.TweepyException as e:
                print(f"❌ Twitter API error for @{username}: {str(e)}")
                if "429" in str(e):  # Rate limit error
                    retry_count += 1
                    if retry_count < max_retries:
                        print(f"⚠️ Rate limit hit for @{username}. Retry {retry_count}/{max_retries} in {wait_time} seconds...")
                        await asyncio.sleep(wait_time)
                        wait_time *= 2
                    else:
                        print(f"❌ Max retries reached for @{username}. Skipping...")
                        return []
                else:
                    print(f"❌ Non-rate-limit error for @{username}: {str(e)}")
                    return []
                    
    except Exception as e:
        print(f"❌ Unexpected error fetching tweets for @{username}: {str(e)}")
        return []

async def fetch_today_tweets(usernames: List[str]) -> List[Dict]:
    """Fetch today's tweets from multiple users using batch processing."""
    client = initialize_twitter_client()
    all_tweets = []
    
    for username in usernames:
        tweets = await fetch_tweets_for_user(username, client)
        all_tweets.extend(tweets)
        
        # Add delay between users to avoid rate limits
        if username != usernames[-1]:  # Don't delay after last user
            print(f"⏳ Waiting 30 seconds before next user...")
            await asyncio.sleep(30)
            
    return all_tweets

# For backward compatibility
def fetch_today_tweets_sync(usernames: List[str]) -> List[Dict]:
    """Synchronous wrapper for fetch_today_tweets."""
    return asyncio.run(fetch_today_tweets(usernames))

def save_tweet_to_supabase(tweet_data):
    """Save a tweet to the Supabase messages table."""
    try:
        # Check if tweet already exists
        if supabase.is_tweet_exists(tweet_data["author"], tweet_data["content"]):
            print(f"⏭️ Tweet from {tweet_data['author']} already exists, skipping...")
            return None

        # Extract metrics from the tweet data
        metrics = tweet_data.get('public_metrics', {})
        
        # Prepare the data to insert with all required fields
        insert_data = {
            "content": tweet_data.get("content", ""),
            "author": tweet_data.get("author", ""),
            "timestamp": tweet_data.get("timestamp", datetime.now(timezone.utc).isoformat()),
            "tweet_url": tweet_data.get("tweet_url", ""),
            "like_count": metrics.get('like_count', 0),
            "retweet_count": metrics.get('retweet_count', 0),
            "reply_count": metrics.get('reply_count', 0),
            "quote_count": metrics.get('quote_count', 0),
            "summarized": False,
            "is_retweet": False,
            "topic": "macro",
            "company": "macro",  # Adding company field back since it exists in schema
            "source": "twitter",  # Adding source field back since it exists in schema
            "private": False
        }

        # Save tweet to database
        response = supabase.client.table("messages").insert(insert_data).execute()
        
        if response.data:
            print(f"✅ Saved tweet from {tweet_data['author']}")
            return response.data
        else:
            print(f"❌ Failed to save tweet from {tweet_data['author']}")
            return None
    except Exception as e:
        print(f"❌ Error saving tweet from {tweet_data['author']}: {e}")
        return None

if __name__ == "__main__":
    print("🚀 Starting Twitter fetch for macro handles...")
    print(f"📊 Will fetch tweets from {len(MACRO_HANDLES)} handles: {', '.join(MACRO_HANDLES)}")
    
    tweets = asyncio.run(fetch_today_tweets(MACRO_HANDLES))
    
    if tweets:
        print(f"\n✅ Successfully fetched {len(tweets)} tweets:")
        for tweet in tweets:
            print(f"\n@{tweet['author']}:")
            print(f"📝 {tweet['content']}")
            print(f"⏰ {tweet['timestamp']}")
            print(f"🔗 {tweet['tweet_url']}")
            if tweet.get('is_thread'):
                print(f"🧵 Thread length: {tweet['thread_length']}")
    else:
        print("\n❌ No tweets found for today.") 