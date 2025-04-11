import os
from datetime import datetime, timezone, timedelta
from typing import List, Dict
from openai import OpenAI
import resend
from dotenv import load_dotenv
from supabase_client import SupabaseClient

# Load environment variables
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
if not client.api_key:
    raise ValueError("OPENAI_API_KEY not found in .env file")

# Resend configuration
RESEND_API_KEY = os.getenv("RESEND_API_KEY")
RESEND_FROM = os.getenv("RESEND_FROM")
RESEND_TO = os.getenv("RESEND_TO")

def get_week_messages(supabase_client: SupabaseClient) -> List[Dict]:
    """Fetch all messages from the current week.
    
    Args:
        supabase_client: SupabaseClient instance
    
    Returns:
        List of message dictionaries from the current week
    """
    # Get the start of the current week (Monday) and end of the week (Sunday)
    today = datetime.now(timezone.utc)
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    
    try:
        # Fetch messages from the week
        messages = supabase_client.get_messages_by_date_range(
            start_of_week.strftime("%Y-%m-%d"),
            end_of_week.strftime("%Y-%m-%d")
        )
        return messages
    except Exception as e:
        print(f"❌ Error fetching messages from Supabase: {e}")
        return []

def group_messages_by_author(messages: List[Dict]) -> Dict[str, List[Dict]]:
    """Group messages by author and format them for the summary.
    
    Args:
        messages: List of message dictionaries
    
    Returns:
        Dictionary with authors as keys and lists of their message dictionaries as values
    """
    grouped = {}
    for msg in messages:
        author = msg.get("author", "Unknown")
        
        if author not in grouped:
            grouped[author] = []
        grouped[author].append(msg)
    
    return grouped

def format_messages_for_summary(grouped_messages: Dict[str, List[Dict]]) -> str:
    """Format grouped messages into a string for the AI summary.
    
    Args:
        grouped_messages: Dictionary of messages grouped by author
    
    Returns:
        Formatted string containing all messages with their URLs
    """
    formatted = []
    for author, messages in grouped_messages.items():
        formatted.append(f"\nTweets from @{author}:")
        for i, msg in enumerate(messages, 1):
            url = msg.get("tweet_url", "")
            formatted.append(f"{i}. {msg['content']}")
            formatted.append(f"   Link: {url}\n")
    
    return "\n".join(formatted)

def generate_ai_summary(messages_text: str) -> str:
    """Generate an AI summary of the messages using OpenAI.
    
    Args:
        messages_text: Formatted string containing all messages
    
    Returns:
        AI-generated summary of the messages
    """
    if not messages_text:
        return "No messages to summarize this week."
    
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        prompt = f"""You are a crypto analyst creating a weekly digest from a list of recent tweets by leading DeFi and protocol-focused Twitter accounts.

Your job is to:
- Identify meaningful announcements, trends, insights, or sentiment in the tweets
- Group similar tweets if applicable (e.g. several tweets about the same update)
- Prioritize newsworthy content: protocol launches, feature updates, partnerships, charts, opinions, and community sentiment
- Be concise but insightful
- Pay special attention to roadmap updates, token metrics, and team changes

✅ Include for each entry:
- A short headline or takeaway (your summary)
- The tweet author and a direct link to the tweet

📝 Format the report exactly like this:

---
📰 Weekly Crypto Protocol Report – {today}

📢 Highlights:

{{% for each significant update %}}
🔹 **[Headline/Takeaway]**
[Tweet content summary...]
By @[author] - [View Tweet](tweet_url)

{{% end for %}}

🧠 Analyst Notes:
- [Key trend or insight 1]
- [Key trend or insight 2]
- [Key trend or insight 3]

---

Here are the raw tweets to analyze:
{messages_text}
"""

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert crypto analyst who excels at identifying key trends and insights from social media updates. You write clear, concise, and insightful summaries."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1000
        )
        
        return response.choices[0].message.content.strip()
    
    except Exception as e:
        print(f"❌ Error generating AI summary: {e}")
        return "Error generating summary."

def send_email_report(summary: str, statistics: Dict) -> bool:
    """Send the weekly report via Resend.com.
    
    Args:
        summary: The AI-generated summary
        statistics: Dictionary containing message statistics
    
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    try:
        # Configure Resend
        resend.api_key = RESEND_API_KEY
        
        # Create email body
        body = f"""
Weekly Social Media Summary Report
================================

{summary}

Statistics:
----------
Total messages: {statistics['total_messages']}
Number of authors: {statistics['num_authors']}

Messages per author:
------------------
{statistics['author_stats']}

Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        # Send email using Resend
        response = resend.Emails.send({
            "from": RESEND_FROM,
            "to": RESEND_TO,
            "subject": f"Weekly Social Media Summary - {datetime.now().strftime('%Y-%m-%d')}",
            "text": body
        })
        
        print("✅ Email report sent successfully")
        return True
        
    except Exception as e:
        print(f"❌ Error sending email: {e}")
        return False

def main():
    """Main function to generate and display the weekly summary."""
    print("📊 Generating weekly summary report...")
    
    # Initialize Supabase client
    supabase = SupabaseClient()
    
    # Get this week's messages
    messages = get_week_messages(supabase)
    if not messages:
        print("No new messages found for this week.")
        return
    
    # Group messages by author
    grouped_messages = group_messages_by_author(messages)
    
    # Format messages for summary
    formatted_messages = format_messages_for_summary(grouped_messages)
    
    # Generate AI summary
    print("\n🤖 Generating AI summary...")
    summary = generate_ai_summary(formatted_messages)
    
    # Prepare statistics
    statistics = {
        'total_messages': len(messages),
        'num_authors': len(grouped_messages),
        'author_stats': '\n'.join(f"- {author}: {len(msgs)} messages" for author, msgs in grouped_messages.items())
    }
    
    # Print the summary
    print("\n📝 Weekly Summary Report")
    print("=" * 50)
    print(summary)
    print("=" * 50)
    
    # Print message statistics
    print("\n📊 Statistics:")
    print(f"Total messages: {statistics['total_messages']}")
    print(f"Number of authors: {statistics['num_authors']}")
    print("\nMessages per author:")
    print(statistics['author_stats'])
    
    # Send email report
    print("\n📧 Sending email report...")
    if send_email_report(summary, statistics):
        # Mark tweets as summarized
        tweet_ids = [msg['id'] for msg in messages]
        if supabase.mark_tweets_as_summarized(tweet_ids):
            print("✅ Marked tweets as summarized")
        else:
            print("❌ Failed to mark tweets as summarized")
    else:
        print("❌ Failed to send email report")

if __name__ == "__main__":
    main() 