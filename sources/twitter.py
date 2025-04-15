#!/usr/bin/env python3
print("Script is starting execution...")

import os
import time
from datetime import datetime, timezone, timedelta
import tweepy
from dotenv import load_dotenv
import sys
import asyncio
from typing import List, Dict, Optional
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

# Rate limiter class
class RateLimiter:
    def __init__(self, max_requests: int, time_window: int):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = {}
        self.last_request_time = 0
        self.min_delay = 5.0  # Increased minimum delay between requests
    
    async def acquire(self, user_id: str = None):
        now = time.time()
        
        # Ensure minimum delay between requests
        if now - self.last_request_time < self.min_delay:
            wait_time = self.min_delay - (now - self.last_request_time)
            print(f"⏳ Waiting {wait_time:.1f} seconds before next request...")
            await asyncio.sleep(wait_time)
            return await self.acquire(user_id)
        
        # Initialize user's request history if not exists
        if user_id not in self.requests:
            self.requests[user_id] = []
        
        # Remove old requests
        self.requests[user_id] = [req for req in self.requests[user_id] if now - req < self.time_window]
        
        # Check if user has exceeded their limit
        if len(self.requests[user_id]) >= self.max_requests:
            # Calculate wait time
            wait_time = self.requests[user_id][0] + self.time_window - now
            if wait_time > 0:
                print(f"⏳ Rate limit reached for user {user_id}. Waiting {wait_time:.1f} seconds...")
                await asyncio.sleep(wait_time)
                return await self.acquire(user_id)
        
        self.requests[user_id].append(now)
        self.last_request_time = now
        return True

# Global rate limiter (More conservative settings)
rate_limiter = RateLimiter(max_requests=3, time_window=900)  # 3 requests per 15 minutes

# Cache for user IDs
user_id_cache = {}

async def get_user_id(client, username: str) -> Optional[str]:
    """Get user ID with caching."""
    if username in user_id_cache:
        return user_id_cache[username]
    
    await rate_limiter.acquire()
    try:
        user = client.get_user(username=username)
        if user.data:
            user_id_cache[username] = user.data.id
            return user.data.id
    except Exception as e:
        print(f"❌ Error looking up user @{username}: {str(e)}")
    return None

async def fetch_tweets_for_user(username: str, client: tweepy.Client) -> List[Dict]:
    """Fetch tweets for a specific user from the last 24 hours.
    
    Args:
        username: Twitter username to fetch tweets from
        client: Initialized tweepy client
        
    Returns:
        List of tweet dictionaries
    """
    try:
        # Get user ID
        user = client.get_user(username=username)
        if not user.data:
            print(f"❌ User @{username} not found")
            return []
        
        user_id = user.data.id
        
        # Calculate time range for last 24 hours
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=24)
        
        # Try to fetch tweets with retry mechanism
        max_retries = 5  # Increased retries but with shorter waits
        retry_count = 0
        base_wait_time = 60  # Start with 1 minute
        
        while retry_count < max_retries:
            try:
                # Fetch tweets excluding retweets and replies
                tweets = client.get_users_tweets(
                    id=user_id,
                    start_time=start_time,
                    end_time=end_time,
                    exclude=["retweets", "replies"],
                    tweet_fields=["created_at", "public_metrics", "entities"],
                    max_results=100
                )
                
                if not tweets.data:
                    print(f"ℹ️ No tweets found for @{username}")
                    return []
                
                # Process tweets
                processed_tweets = []
                for tweet in tweets.data:
                    processed_tweet = {
                        "content": tweet.text,
                        "author": username,
                        "timestamp": tweet.created_at.isoformat(),
                        "tweet_url": f"https://twitter.com/{username}/status/{tweet.id}",
                        "public_metrics": tweet.public_metrics,
                        "company": "macro"  # Default company value
                    }
                    processed_tweets.append(processed_tweet)
                
                print(f"✅ Found {len(processed_tweets)} tweets from @{username}")
                return processed_tweets
                
            except tweepy.TooManyRequests as e:
                retry_count += 1
                if retry_count < max_retries:
                    # Exponential backoff: 1min, 2min, 4min, 8min, 16min
                    wait_time = base_wait_time * (2 ** (retry_count - 1))
                    print(f"⚠️ Rate limit hit for @{username}. Waiting {wait_time/60:.1f} minutes before retry {retry_count}/{max_retries}...")
                    await asyncio.sleep(wait_time)
                else:
                    print(f"❌ Max retries reached for @{username}. Skipping...")
                    return []
                    
            except Exception as e:
                print(f"❌ Error fetching tweets for @{username}: {str(e)}")
                return []
        
    except Exception as e:
        print(f"❌ Error processing @{username}: {str(e)}")
        return []

async def fetch_today_tweets(usernames: List[str]) -> List[Dict]:
    """Fetch today's tweets for multiple usernames sequentially."""
    print("🚀 Starting Twitter fetch for macro handles...")
    print(f"📊 Will fetch tweets from {len(usernames)} handles: {', '.join(usernames)}")
    
    # Initialize Twitter client
    load_dotenv()
    client = tweepy.Client(bearer_token=os.getenv('TWITTER_BEARER_TOKEN'))
    
    # Add initial delay to avoid rate limits
    print("⏳ Adding initial delay to avoid rate limits...")
    await asyncio.sleep(10)  # Reduced initial delay
    
    all_tweets = []
    
    # Process one user at a time with shorter delays
    for i, username in enumerate(usernames):
        print(f"\n📥 Processing user {i+1}/{len(usernames)}: @{username}")
        
        try:
            # Add delay before processing each user
            await asyncio.sleep(3)  # Reduced pre-user delay
            
            # Fetch tweets for this user
            tweets = await fetch_tweets_for_user(username, client)
            all_tweets.extend(tweets)
            
            # Add delay between users
            if i < len(usernames) - 1:
                delay = 15  # Reduced delay between users
                print(f"⏳ Waiting {delay} seconds before next user...")
                await asyncio.sleep(delay)
        except Exception as e:
            print(f"❌ Error processing user @{username}: {str(e)}")
            print("⚠️ Continuing with next user...")
            continue
    
    print(f"\n✅ Successfully fetched {len(all_tweets)} tweets")
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
        metrics = tweet_data.get('metrics', {})
        
        # Prepare the data to insert with all required fields
        insert_data = {
            "company": tweet_data.get("company", "macro"),  # Default to "macro" if not specified
            "source": "twitter",
            "content": tweet_data.get("content", ""),
            "author": tweet_data.get("author", ""),
            "timestamp": tweet_data.get("timestamp", datetime.now(timezone.utc).isoformat()),
            "tweet_url": tweet_data.get("tweet_url", ""),
            "like_count": metrics.get('like_count', 0),
            "retweet_count": metrics.get('retweet_count', 0),
            "reply_count": metrics.get('reply_count', 0),
            "quote_count": metrics.get('quote_count', 0),
            "summarized": False,
            "is_retweet": False,  # Default to false
            "private": False,  # Default to false
            "topic": "macro"  # Default topic
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

def initialize_twitter_client():
    """Initialize the Twitter client with bearer token."""
    try:
        # Set Twitter bearer token from environment
        bearer_token = os.getenv('TWITTER_BEARER_TOKEN')
        if not bearer_token:
            print("❌ TWITTER_BEARER_TOKEN not found in environment variables")
            return None
            
        # Initialize Twitter client
        client = tweepy.Client(bearer_token=bearer_token)
        print("✅ Twitter client initialized")
        return client
        
    except Exception as e:
        print(f"❌ Error initializing Twitter client: {str(e)}")
        return None

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