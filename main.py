import os
import json
import warnings
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from supabase_client import SupabaseClient
from sources.twitter import fetch_today_tweets, MACRO_HANDLES, fetch_tweets_for_user, initialize_twitter_client
import resend
from openai import OpenAI
import re
import tweepy
import time
import asyncio
import sys
from typing import List, Dict, Any, Optional
import openai

# Filter out all syntax warnings from tweepy
warnings.filterwarnings("ignore", category=SyntaxWarning)
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = OpenAI()

# Initialize Supabase client
supabase = SupabaseClient()

# ------------------🔧 Helper Functions ------------------

CACHE_FILE = "seen_tweets.json"

def load_seen_tweets():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            return json.load(f)
    return {}

def save_seen_tweets(cache):
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2)

async def save_tweet_to_supabase(tweet: Dict) -> Optional[Dict]:
    """Save a tweet to the Supabase database."""
    try:
        # Check if tweet already exists
        if supabase.is_tweet_exists(tweet["author"], tweet["content"]):
            print(f"⏭️ Tweet from {tweet['author']} already exists, skipping...")
            return None

        # Extract metrics from the tweet data
        metrics = tweet.get('public_metrics', {})
        
        # Prepare the data to insert with all required fields
        insert_data = {
            "content": tweet.get("content", ""),
            "author": tweet.get("author", ""),
            "timestamp": tweet.get("timestamp", datetime.now(timezone.utc).isoformat()),
            "tweet_url": tweet.get("tweet_url", ""),
            "like_count": metrics.get('like_count', 0),
            "retweet_count": metrics.get('retweet_count', 0),
            "reply_count": metrics.get('reply_count', 0),
            "quote_count": metrics.get('quote_count', 0),
            "summarized": False,
            "is_retweet": False,
            "topic": "macro",
            "private": False
        }

        # Save tweet to database
        response = supabase.client.table("messages").insert(insert_data).execute()
        
        if response.data:
            print(f"✅ Saved tweet from {tweet['author']}")
            return response.data
        else:
            print(f"❌ Failed to save tweet from {tweet['author']}")
            return None
    except Exception as e:
        print(f"❌ Error saving tweet: {str(e)}")
        return None

async def generate_ai_summary(tweets: List[Dict]) -> str:
    """Generate an AI summary of the tweets."""
    try:
        # Format tweets for summary
        formatted_tweets = []
        for tweet in tweets:
            formatted_tweet = f"@{tweet['author']}: {tweet['content']} [Link]({tweet['tweet_url']})"
            formatted_tweets.append(formatted_tweet)
        
        # Join tweets with newlines
        tweet_text = "\n\n".join(formatted_tweets)
        
        # Generate summary using OpenAI
        prompt = f"""
You are a senior hedge fund analyst at w3.wave, writing a daily intelligence briefing for internal portfolio managers.

Your job is to analyze the following tweets from macroeconomic and crypto market experts and extract investment-relevant insights.

📌 Structure your output under these headers:
🧠 Macro  
🏛️ Politics & Geopolitics  
📊 Traditional Markets  
💰 Crypto Markets  
🔄 Observed Shifts in Sentiment or Tone

For each bullet point:
- Capture the full context of the tweet — explain *what is being said*, *why it matters*, and *what the implication is*.
- Do not summarize too briefly. Your job is to synthesize the full message for an investment audience, not just give headlines.
- When multiple tweets from one author build on the same point, combine them into a single, well-rounded insight.
- Always include the author handle and a full tweet link in Markdown format. Use multiple links if needed.

🎯 Focus on signal, not noise:
- Extract actual market commentary, forecasts, emerging risks, sentiment signals, and macro/crypto links.
- Omit memes, jokes, and overly vague takes.

Here are the tweets to analyze:
"""
        
        response = client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": tweet_text}
            ],
            temperature=0.4,
            top_p=0.9,
            max_tokens=2000,
            frequency_penalty=0.4,
            presence_penalty=0.5
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        print(f"❌ Error generating summary: {str(e)}")
        return ""

async def send_email_report(summary: str) -> None:
    """Send the email report using Resend."""
    try:
        # Format email content
        email_content = format_email_html(summary)
        
        # Configure Resend
        resend.api_key = os.getenv("RESEND_API_KEY")
        if not resend.api_key:
            raise ValueError("RESEND_API_KEY not found in environment variables")
            
        # Get email configuration
        from_email = os.getenv("RESEND_FROM", "onboarding@resend.dev")
        to_email = os.getenv("RESEND_TO", "philippbeer86@gmail.com")
        
        if not from_email or not to_email:
            raise ValueError("Email configuration missing. Please set RESEND_FROM and RESEND_TO in .env")
        
        # Send email using Resend
        response = resend.Emails.send({
            "from": from_email,
            "to": to_email,
            "subject": f"Daily Macro Report - {datetime.now().strftime('%Y-%m-%d')}",
            "html": email_content
        })
        
        if response:
            print("✅ Email report sent successfully")
        else:
            print("❌ Failed to send email report")
            
    except Exception as e:
        print(f"❌ Error sending email: {str(e)}")

def format_email_html(summary_text: str) -> str:
    """Format the AI summary in a super clean plain text style HTML email."""
    return f"""
    <html>
      <body style="font-family: monospace; font-size: 14px; color: #000; line-height: 1.6;">
        <pre style="white-space: pre-wrap;">
📬 Daily Macro & Crypto Intelligence Report
==========================================

{summary_text}

==========================================

Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        </pre>
      </body>
    </html>
    """

def filter_and_sort_tweets(tweets: list, min_engagement: int = 0) -> list:
    """Filter and sort tweets by engagement metrics.
    
    Args:
        tweets: List of tweet dictionaries
        min_engagement: Minimum total engagement (likes + retweets) to include
        
    Returns:
        List of filtered and sorted tweets
    """
    # Calculate total engagement for each tweet
    for tweet in tweets:
        tweet['total_engagement'] = (
            tweet.get('like_count', 0) + 
            tweet.get('retweet_count', 0) * 2 +  # Weight retweets more heavily
            tweet.get('reply_count', 0) * 3 +    # Weight replies even more
            tweet.get('quote_count', 0) * 2      # Weight quotes like retweets
        )
    
    # Filter out low-engagement tweets
    filtered_tweets = [t for t in tweets if t['total_engagement'] >= min_engagement]
    
    # Sort by total engagement
    filtered_tweets.sort(key=lambda x: x['total_engagement'], reverse=True)
    
    print(f"📊 Found {len(filtered_tweets)} tweets to analyze")
    if filtered_tweets:
        print(f"📊 Top tweet engagement: {filtered_tweets[0]['total_engagement']}")
    
    return filtered_tweets

def generate_summary_with_openai(prompt: str) -> str:
    """Generate a summary using OpenAI's API.
    
    Args:
        prompt: The prompt to send to OpenAI
        
    Returns:
        str: The generated summary
    """
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert macro analyst who excels at identifying key trends and insights from social media updates. You write clear, concise, and insightful summaries."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1000
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"❌ Error generating summary with OpenAI: {str(e)}")
        return "Error generating summary with OpenAI."

def is_meaningful_tweet(tweet: str) -> bool:
    """Check if a tweet is meaningful (not a reply or @mention).
    
    Args:
        tweet: The tweet text to check
        
    Returns:
        bool: True if the tweet is meaningful, False if it's a reply or @mention
    """
    # Remove any leading/trailing whitespace
    tweet = tweet.strip()
    
    # Return False if tweet starts with @ (reply or mention)
    if tweet.startswith('@'):
        return False
        
    return True

def filter_meaningful_tweets(tweets: List[Dict]) -> List[Dict]:
    """Filter out non-meaningful tweets (replies and @mentions).
    
    Args:
        tweets: List of tweet dictionaries
        
    Returns:
        List of filtered tweet dictionaries
    """
    return [tweet for tweet in tweets if is_meaningful_tweet(tweet['content'])]

# ------------------📦 Main Execution ------------------

async def async_main():
    """Main async function to orchestrate the daily report generation."""
    print("🧠 Starting daily report generation...")
    
    # List of users to monitor
    users = [
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
    
    print(f"📊 Will monitor {len(users)} Twitter handles")
    
    # Initialize Twitter client
    twitter_client = initialize_twitter_client()
    if not twitter_client:
        print("❌ Failed to initialize Twitter client")
        return
    
    print("\n📥 Fetching new tweets from Twitter...")
    
    # Fetch tweets for each user
    all_tweets = []
    for i, username in enumerate(users, 1):
        print(f"\n🔍 Processing user {i}/{len(users)}: @{username}")
        tweets = await fetch_tweets_for_user(username, twitter_client)
        if tweets:
            print(f"✅ Found {len(tweets)} tweets from @{username}")
            all_tweets.extend(tweets)
        else:
            print(f"ℹ️ No tweets found for @{username}")
        
        # Add a delay between users to avoid rate limits
        if i < len(users):
            delay = 30  # Increased from 15 to 30 seconds
            print(f"⏳ Waiting {delay} seconds before next user...")
            await asyncio.sleep(delay)
    
    if not all_tweets:
        print("\n❌ No tweets found for any user")
        return
    
    print(f"\n📊 Total tweets collected: {len(all_tweets)}")
    
    # Save tweets to Supabase
    print("\n💾 Saving tweets to database...")
    for tweet in all_tweets:
        try:
            await save_tweet_to_supabase(tweet)
        except Exception as e:
            print(f"❌ Error saving tweet: {str(e)}")
    
    print("\n📝 Generating AI summary...")
    summary = await generate_ai_summary(all_tweets)
    
    print("\n📧 Sending email report...")
    await send_email_report(summary)
    
    print("\n✅ Daily report generation completed!")

def main():
    """Main function to run the script."""
    print("Script is starting execution...")
    asyncio.run(async_main())

def generate_and_send_report():
    """Generate AI summary and send email report for today's tweets."""
    # Load environment variables
    load_dotenv()
    
    # Initialize clients
    supabase = SupabaseClient()
    
    # Import the list of handles to monitor
    users = MACRO_HANDLES
    
    print("🧠 Starting daily report generation...")
    print(f"📊 Will monitor {len(users)} Twitter handles")
    
    # Step 1: Fetch new tweets from Twitter and save to database
    print("\n📥 Fetching new tweets from Twitter...")
    all_tweets = []
    
    for i, username in enumerate(users):
        print(f"\n🔍 Processing user {i+1}/{len(users)}: @{username}")
        new_tweets = fetch_today_tweets([username])  # Process one user at a time
        
        if new_tweets:
            print(f"📥 Found {len(new_tweets)} new tweets to save")
            for tweet in new_tweets:
                print(f"\n💾 Attempting to save tweet from @{tweet['author']}:")
                print(f"📝 Content: {tweet['content'][:100]}...")
                saved_data = save_tweet_to_supabase(supabase, tweet)
                if saved_data:
                    print(f"✅ Successfully saved tweet from @{tweet['author']}")
                    tweet['saved_data'] = saved_data
                    all_tweets.append(tweet)
                else:
                    print(f"❌ Failed to save tweet from @{tweet['author']}")
        else:
            print(f"📥 No new tweets found for @{username}")
        
        # Add delay between users to avoid rate limits
        if i < len(users) - 1:  # Don't delay after the last user
            delay = 30  # 30 seconds between users
            print(f"\n⏳ Waiting {delay} seconds before processing next user...")
            time.sleep(delay)
    
    if not all_tweets:
        print("📥 No new tweets found on Twitter today")
    
    # Step 2: Get today's non-summarized tweets from database
    print("\n🔍 Checking database for non-summarized tweets...")
    today = datetime.now(timezone.utc).date()
    print(f"📅 Looking for tweets from: {today.isoformat()}")
    tweets_to_process = supabase.get_tweets_by_date(today)
    
    if not tweets_to_process:
        print("✅ No tweets to analyze today.")
        return
    
    print(f" Found {len(tweets_to_process)} tweets to analyze")
    
    # Step 3: Filter and sort tweets by engagement
    print("\n📊 Filtering and sorting tweets by engagement...")
    tweets_to_process = filter_and_sort_tweets(tweets_to_process)
    
    if not tweets_to_process:
        print("✅ No high-engagement tweets to analyze today.")
        return
    
    # Step 4: Generate AI summary
    print("\n🤖 Generating AI summary...")
    summary = generate_ai_summary(tweets_to_process)
    
    # Step 5: Send email report
    print("\n📧 Sending email report...")
    asyncio.run(send_email_report(summary))
    
    # Step 6: Mark tweets as summarized after successful email delivery
    tweet_ids = [tweet['id'] for tweet in tweets_to_process]
    if supabase.mark_tweets_as_summarized(tweet_ids):
        print(f"✅ Successfully marked {len(tweet_ids)} tweets as summarized")
    else:
        print("❌ Failed to mark tweets as summarized")

def reset_today_summarized_status():
    """Reset the summarized status of today's tweets to False."""
    # Load environment variables
    load_dotenv()
    
    # Initialize Supabase client
    supabase = SupabaseClient()
    
    print("🔄 Resetting summarized status for today's tweets...")
    
    # Get today's date range
    today = datetime.now(timezone.utc).date()
    next_day = today + timedelta(days=1)
    
    try:
        # Update all tweets from today to set summarized = False
        response = supabase.client.table("messages")\
            .update({"summarized": False})\
            .gte("timestamp", today.isoformat())\
            .lt("timestamp", next_day.isoformat())\
            .execute()
        
        if response.data:
            print(f"✅ Successfully reset summarized status for {len(response.data)} tweets")
            return True
        else:
            print("❌ No tweets found for today")
            return False

    except Exception as e:
        print(f"❌ Error resetting summarized status: {e}")
        return False

def test_twitter_api():
    """Test Twitter API connection and tweet fetching."""
    print("\n🔍 Testing Twitter API connection...")
    
    # Load environment variables
    load_dotenv()
    
    # Initialize Twitter client
    BEARER_TOKEN = os.getenv('TWITTER_BEARER_TOKEN')
    if not BEARER_TOKEN:
        print("❌ Twitter Bearer Token not found in environment variables")
        return False
    
    print(f"🔑 Twitter Bearer Token: {BEARER_TOKEN[:10]}...{BEARER_TOKEN[-10:]}")
    
    try:
        client = tweepy.Client(bearer_token=BEARER_TOKEN)
        print("✅ Twitter client initialized successfully")
        
        # Test with one user
        test_user = "qthomp"
        print(f"\n🔍 Testing tweet fetch for @{test_user}...")
        
        # Get user ID
        user = client.get_user(username=test_user)
        if not user.data:
            print(f"❌ Could not find user @{test_user}")
            return False
        
        print(f"✅ Found user ID: {user.data.id}")
        
        # Calculate time range (last 24 hours)
        now = datetime.now(timezone.utc)
        start_time = now - timedelta(hours=24)
        start_time_str = start_time.strftime('%Y-%m-%dT%H:%M:%SZ')
        
        print(f"📅 Fetching tweets since: {start_time_str}")
        
        # Fetch tweets
        tweets = client.get_users_tweets(
            id=user.data.id,
            start_time=start_time_str,
            tweet_fields=["created_at", "id", "text", "referenced_tweets", "public_metrics"],
            expansions=["referenced_tweets.id"],
            max_results=10
        )
        
        if not tweets.data:
            print(f"ℹ️ No tweets found for @{test_user} in the last 24 hours")
        else:
            print(f"✅ Found {len(tweets.data)} tweets for @{test_user}")
            for tweet in tweets.data:
                print(f"\n📝 Tweet: {tweet.text[:100]}...")
                print(f"⏰ Created at: {tweet.created_at}")
                print(f"📊 Engagement: {tweet.public_metrics}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing Twitter API: {str(e)}")
        return False

if __name__ == "__main__":
    main()
