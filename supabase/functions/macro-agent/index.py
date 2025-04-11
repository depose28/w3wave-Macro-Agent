from datetime import datetime
import json
import os
import httpx
import tweepy
import openai
from resend import Resend
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize clients
DB_URL = os.getenv('DB_URL')
DB_SERVICE_KEY = os.getenv('DB_SERVICE_KEY')

twitter_client = tweepy.Client(
    bearer_token=os.getenv('TWITTER_BEARER_TOKEN'),
    wait_on_rate_limit=True
)

openai.api_key = os.getenv('OPENAI_API_KEY')
resend = Resend(api_key=os.getenv('SENDER_API_KEY'))

def get_tweets_from_supabase(date):
    """Get tweets from Supabase database."""
    try:
        headers = {
            'apikey': DB_SERVICE_KEY,
            'Authorization': f'Bearer {DB_SERVICE_KEY}',
            'Content-Type': 'application/json'
        }
        response = httpx.get(
            f'{DB_URL}/rest/v1/messages',
            headers=headers,
            params={'date': 'eq.' + date}
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Error getting tweets from Supabase: {str(e)}")
        return None

def generate_ai_summary(tweets):
    """Generate AI summary of tweets."""
    prompt = """You are a senior hedge fund analyst specializing in macro analysis. 
    Analyze the following tweets and provide a concise, insightful summary focusing on high-signal insights.
    Structure your analysis into clear sections with emoji headers:
    
    🧠 Macro
    🏛️ Politics & Geopolitics
    📊 Traditional Markets
    💰 Crypto Markets
    🔄 Observed Shifts in Sentiment or Tone
    
    For each insight, include the source tweet URL in parentheses.
    Focus on actionable insights and emerging trends.
    Keep the analysis professional and data-driven."""
    
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": json.dumps(tweets)}
            ],
            temperature=0.7,
            max_tokens=1000
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Error generating AI summary: {str(e)}")
        return None

def format_email_html(summary_text):
    """Format the email content with HTML styling."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    html_content = """
    <html>
    <body style="font-family: Arial, sans-serif; font-size: 14px; color: #333; line-height: 1.6;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <h1 style="color: #2c3e50; border-bottom: 2px solid #eee; padding-bottom: 10px;">
                Daily Macro Update
            </h1>
            <div style="margin-top: 20px;">
                {0}
            </div>
            <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee; color: #666; font-size: 12px;">
                Generated at {1}
            </div>
        </div>
    </body>
    </html>
    """.format(summary_text.replace('\n', '<br>'), timestamp)
    return html_content

def send_email_report(summary):
    """Send the email report."""
    try:
        html_content = format_email_html(summary)
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        plain_text = "Daily Macro Update\n\n{0}\n\nGenerated at {1}".format(summary, timestamp)
        
        resend.emails.send({
            "from": os.getenv('EMAIL_SENDER'),
            "to": os.getenv('EMAIL_RECIPIENT'),
            "subject": "Daily Macro Update",
            "html": html_content,
            "text": plain_text
        })
        return True
    except Exception as e:
        logger.error(f"Error sending email: {str(e)}")
        return False

def main():
    try:
        # Get today's tweets from database
        today = datetime.now().date().isoformat()
        tweets = get_tweets_from_supabase(today)

        if not tweets:
            logger.info("No tweets found for today")
            return {"status": "success", "message": "No tweets found for today"}

        # Generate AI summary
        summary = generate_ai_summary(tweets)
        if not summary:
            logger.error("Failed to generate AI summary")
            return {"status": "error", "message": "Failed to generate AI summary"}

        # Send email report
        if send_email_report(summary):
            logger.info("Email report sent successfully")
            return {"status": "success", "message": "Email report sent successfully"}
        else:
            logger.error("Failed to send email report")
            return {"status": "error", "message": "Failed to send email report"}

    except Exception as e:
        logger.error(f"Error in main function: {str(e)}")
        return {"status": "error", "message": str(e)}

# Supabase Edge Function handler
def handler(request):
    try:
        result = main()
        return {
            "statusCode": 200,
            "body": json.dumps(result)
        }
    except Exception as e:
        logger.error(f"Error in handler: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"status": "error", "message": str(e)})
        }

if __name__ == "__main__":
    main() 