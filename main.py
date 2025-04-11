import os
import json
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from supabase_client import SupabaseClient
from sources.twitter import fetch_today_tweets
import resend
from openai import OpenAI
import re

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

def save_tweet_to_supabase(supabase_client, tweet_data):
    """Save a tweet to the Supabase messages table.
    
    Args:
        supabase_client: SupabaseClient instance
        tweet_data: dict containing tweet data with the following keys:
            - company: text (company/user identifier)
            - source: text (always "twitter")
            - content: text (tweet content)
            - author: text (tweet author)
            - timestamp: timestamp with time zone (tweet creation time)
    
    Returns:
        dict: Response data from Supabase if successful
        None: If there was an error saving the tweet or if tweet already exists
    """
    try:
        # Check if tweet already exists
        if supabase_client.is_tweet_exists(tweet_data["author"], tweet_data["content"]):
            print(f"⏭️ Tweet from {tweet_data['author']} already exists, skipping...")
            return None

        # created_at will be set automatically by Supabase
        response = supabase_client.client.table("messages").insert(tweet_data).execute()
        
        if response.data:
            print(f"✅ Saved tweet from {tweet_data['author']}")
            return response.data[0]  # Return the first (and only) inserted record
        else:
            print(f"❌ No data returned when saving tweet from {tweet_data['author']}")
            return None
            
    except Exception as e:
        print(f"❌ Error saving tweet: {str(e)}")
        return None

def generate_ai_summary(tweets: list) -> str:
    """Generate an AI summary of the tweets using OpenAI.
    
    Args:
        tweets: List of tweet dictionaries
    
    Returns:
        str: AI-generated summary
    """
    if not tweets:
        return "No tweets to summarize today."
    
    try:
        # Format tweets with engagement metrics and URLs
        formatted_tweets = "\n".join([
            f"@{tweet['author']} ({tweet['total_engagement']} engagement): {tweet['content']}\nURL: {tweet.get('tweet_url', 'N/A')}"
            for tweet in tweets
        ])
        
        # Initialize OpenAI client
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Generate summary
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": """
You are a senior macro & crypto analyst at a hedge fund. You analyze market commentary from high-signal Twitter accounts to extract daily insights. Your output will be read by PMs and CIOs.

Your job is NOT to summarize tweets — it's to interpret and cluster them into evolving market narratives.

## Guidelines:
- Group tweets by shared themes or developing narratives (e.g. "Dollar Liquidity Pressure", "Risk-On Signals", "Institutional Flow", "Crypto Beta Rotation").
- Use institutional tone: informative, confident, concise. No fluff.
- If multiple tweets discuss the same theme, synthesize the core insight and attribute key quotes.
- Extract market sentiment (bullish/bearish/neutral) and tone (e.g. urgent, cautious, euphoric) where relevant.
- Tag tweet function with emojis: 🧠 Insight, 📊 Data/Chart, 🔮 Forecast, 🎙️ Commentary, 🚨 News Reaction
- Flag contrarian takes or sentiment shifts (e.g. "This poster was previously bearish and now flipping bullish").
- Only include content with market relevance. Discard jokes, memes, off-topic banter.

## Output Structure:
🧠 Macro
- Key insights and implications
- Source tweets with URLs directly under each insight they support

🌍 Politics & Geopolitics
- Key insights and implications
- Source tweets with URLs directly under each insight they support

📉 Traditional Markets
- Key insights and implications
- Source tweets with URLs directly under each insight they support

🪙 Crypto Markets
- Key insights and implications
- Source tweets with URLs directly under each insight they support

🔍 Observed Shifts in Sentiment or Tone
- Notable changes in market sentiment
- Contrarian views and their rationale
- Source tweets with URLs for sentiment evidence

Be sharp. Think like you're prepping a morning call for an investment committee.
"""
                },
                {
                    "role": "user",
                    "content": f"""
Below are today's tweets from our tracked accounts, with engagement metrics and source URLs.

Please analyze them according to the guidelines and structure above. Focus on extracting actionable insights and evolving narratives.

For each insight or point you make, include the relevant tweet URL directly underneath it, formatted as:
Source: @author - URL

Tweets:
{formatted_tweets}

Remember to:
1. Group by themes/narratives
2. Tag insights with appropriate emojis
3. Note any sentiment shifts
4. Include source URLs under each point they support
"""
                }
            ],
            temperature=0.7,  # Slightly higher temperature for more narrative synthesis
            max_tokens=2000   # Increased token limit for more detailed analysis
        )
        
        return response.choices[0].message.content.strip()
    
    except Exception as e:
        print(f"❌ Error generating AI summary: {e}")
        return "Error generating summary."

def format_email_html(summary_text: str) -> str:
    # Convert markdown bold (if any) to <strong>
    summary_text = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", summary_text)

    # Format section headers like "🧠 Macro" into <h2>
    headers = [
        "🧠 Macro",
        "🌍 Politics & Geopolitics",
        "📉 Traditional Markets",
        "🪙 Crypto Markets",
        "🔍 Observed Shifts in Sentiment or Tone"
    ]
    for header in headers:
        summary_text = summary_text.replace(
            header, f'<h2 style="font-size: 16px; margin: 24px 0 12px;">{header}</h2>'
        )

    # Format numbered bullet points into <p>
    summary_text = re.sub(
        r"^\d+\.\s(.+?)(?=\n|$)", 
        r'<p style="margin: 0 0 10px;">• \1</p>', 
        summary_text, 
        flags=re.MULTILINE
    )

    # Format "Source: @user - https://..." lines into links
    summary_text = re.sub(
        r"(Source[s]?:\s*@[\w]+)\s*-\s*(https://twitter\.com/\S+)",
        r'<p style="margin: 0 0 16px;"><em>\1</em> – <a href="\2" target="_blank">View Tweet</a></p>',
        summary_text
    )

    # Replace double newlines (if any remain) with break
    summary_text = summary_text.replace("\n\n", "<br><br>")

    # Remove leftover single newlines
    summary_text = summary_text.replace("\n", " ")

    # Wrap it in a basic HTML body
    return f"""
    <html>
      <body style="font-family: Arial, sans-serif; font-size: 14px; color: #333; line-height: 1.6;">
        <h1 style="font-size: 18px; margin-bottom: 20px;">📬 Daily Social Media Summary Report</h1>
        {summary_text}
        <hr style="border: none; border-top: 1px solid #ccc; margin: 32px 0;">
        <p style="font-size: 12px; color: #999;">Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
      </body>
    </html>
    """

def send_email_report(summary: str, tweets: list) -> bool:
    """Send the daily report via Resend.com.
    
    Args:
        summary: The AI-generated summary
        tweets: List of tweet dictionaries
    
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    try:
        # Configure Resend with credentials from .env
        resend.api_key = os.getenv("SENDER_API_KEY")
        
        # Get email addresses
        from_email = os.getenv("FROM_EMAIL")
        to_email = os.getenv("TO_EMAIL")
        
        if not from_email or not to_email:
            print("❌ Email addresses not configured")
            return False
        
        # Format the email content with HTML
        html_content = format_email_html(summary)
        
        # Create plain text version
        plain_text = f"""
Daily w3.wave Macro Update
=========================

{summary}

Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        # Send email using Resend with both HTML and plain text
        response = resend.Emails.send({
            "from": from_email,
            "to": to_email,
            "subject": "Daily w3.wave Macro Update",
            "html": html_content,
            "text": plain_text
        })
        
        print("✅ Email report sent successfully")
        return True
        
    except Exception as e:
        print(f"❌ Error sending email: {e}")
        return False

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

# ------------------📦 Main Execution ------------------

def main():
    # Load environment variables
    load_dotenv()
    
    # Initialize clients
    supabase = SupabaseClient()
    
    # Configure users to monitor
    users = [
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
    
    print("🧠 Starting daily tweet analysis...")
    
    # Step 1: Fetch new tweets from Twitter and save to database
    print("\n📥 Fetching new tweets from Twitter...")
    new_tweets = fetch_today_tweets(users)
    
    if new_tweets:
        print(f"📥 Found {len(new_tweets)} new tweets to save")
        for tweet in new_tweets:
            saved_data = save_tweet_to_supabase(supabase, tweet)
            if saved_data:
                tweet['saved_data'] = saved_data
    else:
        print("📥 No new tweets found on Twitter today")
    
    # Step 2: Get today's non-summarized tweets from database
    print("\n🔍 Checking database for non-summarized tweets...")
    today = datetime.now(timezone.utc).date()
    tweets_to_process = supabase.get_tweets_by_date(today)
    
    if not tweets_to_process:
        print("✅ No tweets to analyze today.")
        return
    
    print(f"📊 Found {len(tweets_to_process)} tweets to analyze")
    
    # Step 3: Filter and sort tweets by engagement
    print("\n📊 Filtering and sorting tweets by engagement...")
    tweets_to_process = filter_and_sort_tweets(tweets_to_process)
    
    if not tweets_to_process:
        print("✅ No high-engagement tweets to analyze today.")
        return
    
    # Step 4: Generate AI summary
    print("\n🤖 Generating AI summary...")
    summary = generate_ai_summary(tweets_to_process)
    
    # Step 5: Store AI report in database
    print("\n💾 Storing AI report in database...")
    # Get the Supabase IDs of the tweets we just saved
    tweet_ids = []
    for tweet in tweets_to_process:
        # Try to get the ID from the saved tweet data
        if 'saved_data' in tweet and tweet['saved_data'] and 'id' in tweet['saved_data']:
            tweet_ids.append(tweet['saved_data']['id'])
        else:
            print(f"⚠️ Warning: Could not find ID for tweet from {tweet['author']}")
    
    report_data = {
        "summary": summary,
        "tweet_ids": tweet_ids,
        "date": today.isoformat(),
        "email_sent": False
    }
    stored_report = supabase.store_ai_report(report_data)
    if stored_report:
        print("✅ Successfully stored AI report")
    else:
        print("❌ Failed to store AI report")
        return
    
    # Step 6: Send email report
    print("\n📧 Sending email report...")
    if send_email_report(summary, tweets_to_process):
        # Step 7: Mark tweets as summarized after successful email delivery
        tweet_ids = [tweet['id'] for tweet in tweets_to_process]
        if supabase.mark_tweets_as_summarized(tweet_ids):
            print(f"✅ Successfully marked {len(tweet_ids)} tweets as summarized")
            
            # Update report to indicate email was sent
            supabase.client.table("ai_reports")\
                .update({"email_sent": True})\
                .eq("id", stored_report["id"])\
                .execute()
            print("✅ Updated report status to email sent")
        else:
            print("❌ Failed to mark tweets as summarized")
    else:
        print("❌ Failed to send email report")

def generate_and_send_report():
    """Generate AI summary and send email report for today's tweets."""
    # Load environment variables
    load_dotenv()
    
    # Initialize clients
    supabase = SupabaseClient()
    
    print("🧠 Starting daily report generation...")
    
    # Get today's non-summarized tweets from database
    print("\n🔍 Checking database for non-summarized tweets...")
    today = datetime.now(timezone.utc).date()
    tweets_to_process = supabase.get_tweets_by_date(today)
    
    if not tweets_to_process:
        print("✅ No tweets to analyze today.")
        return
    
    print(f"📊 Found {len(tweets_to_process)} tweets to analyze")
    
    # Filter and sort tweets by engagement
    print("\n📊 Filtering and sorting tweets by engagement...")
    tweets_to_process = filter_and_sort_tweets(tweets_to_process)
    
    if not tweets_to_process:
        print("✅ No high-engagement tweets to analyze today.")
        return
    
    # Generate AI summary
    print("\n🤖 Generating AI summary...")
    summary = generate_ai_summary(tweets_to_process)
    
    # Store AI report in database
    print("\n💾 Storing AI report in database...")
    tweet_ids = [tweet['id'] for tweet in tweets_to_process]
    report_data = {
        "summary": summary,
        "tweet_ids": tweet_ids,
        "date": today.isoformat(),
        "email_sent": False
    }
    stored_report = supabase.store_ai_report(report_data)
    if stored_report:
        print("✅ Successfully stored AI report")
    else:
        print("❌ Failed to store AI report")
        return
    
    # Send email report
    print("\n📧 Sending email report...")
    if send_email_report(summary, tweets_to_process):
        # Mark tweets as summarized after successful email delivery
        if supabase.mark_tweets_as_summarized(tweet_ids):
            print(f"✅ Successfully marked {len(tweet_ids)} tweets as summarized")
            
            # Update report to indicate email was sent
            supabase.client.table("ai_reports")\
                .update({"email_sent": True})\
                .eq("id", stored_report["id"])\
                .execute()
            print("✅ Updated report status to email sent")
        else:
            print("❌ Failed to mark tweets as summarized")
    else:
        print("❌ Failed to send email report")

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

if __name__ == "__main__":
    # First reset the summarized status
    if reset_today_summarized_status():
        # Then generate and send the report
        generate_and_send_report()
