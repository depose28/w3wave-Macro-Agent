import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from supabase_client import SupabaseClient
import requests

def get_uncovered_metrics(supabase: SupabaseClient) -> Optional[Dict]:
    """Get the latest uncovered metrics from Supabase."""
    try:
        # Get the latest uncovered metrics
        result = supabase.client.table("fluid_metrics") \
            .select("*") \
            .eq("covered", False) \
            .order("created_at", desc=True) \
            .limit(1) \
            .execute()
        
        if result.data:
            return result.data[0]
        return None
    except Exception as e:
        print(f"❌ Error fetching uncovered metrics: {e}")
        return None

def get_relevant_tweets(supabase: SupabaseClient, start_date: str, end_date: str) -> List[Dict]:
    """Get relevant tweets for the date range."""
    try:
        # Convert string dates to datetime for comparison
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        
        # Get tweets from the messages table
        result = supabase.client.table("messages") \
            .select("*") \
            .gte("created at", start.isoformat()) \
            .lte("created at", end.isoformat()) \
            .execute()
        
        return result.data
    except Exception as e:
        print(f"❌ Error fetching tweets: {e}")
        return []

def format_tweet_summary(tweets: List[Dict]) -> str:
    """Format tweets into a summary for the report."""
    if not tweets:
        return "No relevant tweets found for this period."
    
    summary = []
    for tweet in tweets:
        # Format each tweet (using content field instead of text)
        tweet_text = tweet.get("content", "").replace("\n", " ")
        summary.append(f"- {tweet_text}")
    
    return "\n".join(summary)

def generate_report(metrics: Dict, tweets: List[Dict]) -> str:
    """Generate the full report using metrics and tweets."""
    report = f"""🔹 **Project: Fluid**

**Narrative:**
Recent social media activity and community engagement:
{format_tweet_summary(tweets)}

**Fundamentals:**
Key metrics for the week of {metrics['start_date']} to {metrics['end_date']}:
"""

    if not metrics.get('metrics'):
        report += "\nNo metrics data available for this period."
    else:
        report += f"""
- TVL: {metrics['metrics']['tvl']['formatted_current']} ({metrics['metrics']['tvl']['formatted_change']} WoW)
- Active Users (Monthly): {metrics['metrics']['user_mau']['formatted_current']} ({metrics['metrics']['user_mau']['formatted_change']} WoW)
- Active Users (Weekly): {metrics['metrics']['active_addresses_weekly']['formatted_current']} ({metrics['metrics']['active_addresses_weekly']['formatted_change']} WoW)
- Net Deposits: {metrics['metrics']['net_deposits']['formatted_current']} ({metrics['metrics']['net_deposits']['formatted_change']} WoW)
- Revenue: {metrics['metrics']['revenue']['formatted_current']} ({metrics['metrics']['revenue']['formatted_change']} WoW)
- Token Price: {metrics['metrics']['price']['formatted_current']} ({metrics['metrics']['price']['formatted_change']} WoW)

**Raw Metrics Table:**

| Metric             | This Week | Last Week | Change     |
|--------------------|-----------|-----------|------------|"""

        # Add each metric to the table
        for metric, data in metrics['metrics'].items():
            metric_name = metric.replace("_", " ").title()
            if metric == "active_addresses_weekly":
                metric_name = "Active Users (WAU)"
            elif metric == "user_mau":
                metric_name = "Active Users (MAU)"
            
            report += f"\n| {metric_name:<18} | {data['formatted_current']:<9} | {data['formatted_previous']:<9} | {data['formatted_change']:<9} |"

    report += f"""

---
Dashboard: https://tokenterminal.com/terminal/projects/fluid
Report generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
Date Range: {metrics['start_date']} to {metrics['end_date']}"""

    return report

def send_report(report: str) -> bool:
    """Send the report via email using Resend."""
    try:
        # Get email settings from environment
        sender = os.getenv("EMAIL_SENDER")
        recipient = os.getenv("EMAIL_RECIPIENT")
        
        if not all([sender, recipient]):
            print("❌ Missing email configuration")
            return False
        
        # Create the email message
        subject = f"Fluid Protocol Weekly Report ({datetime.now().strftime('%Y-%m-%d')})"
        html_content = report.replace("\n", "<br>")
        html_content = f"<html><body>{html_content}</body></html>"
        
        # Send the email using Resend
        response = requests.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {os.getenv('SENDER_API_KEY')}",
                "Content-Type": "application/json"
            },
            json={
                "from": sender,
                "to": recipient,
                "subject": subject,
                "html": html_content
            }
        )
        
        if response.status_code in [200, 201, 202]:
            print("✅ Report sent successfully")
            return True
        else:
            print(f"❌ Error sending report: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error sending report: {e}")
        return False

def main():
    """Main function to generate and send the Fluid report."""
    try:
        # Initialize Supabase client
        supabase = SupabaseClient()
        
        # Get latest uncovered metrics
        metrics = get_uncovered_metrics(supabase)
        if not metrics:
            print("❌ No uncovered metrics found")
            return
        
        # Get relevant tweets
        tweets = get_relevant_tweets(supabase, metrics["start_date"], metrics["end_date"])
        print(f"📱 Found {len(tweets)} relevant tweets")
        
        # Generate the report
        print("\n📊 Generating report...")
        report = generate_report(metrics, tweets)
        print("\n📝 Report Preview:")
        print(report)
        
        # Send the report
        if send_report(report):
            # Mark metrics as covered
            supabase.mark_metrics_as_covered(metrics["id"])
            print("✅ Process completed successfully")
        
    except Exception as e:
        print(f"❌ Error in main process: {e}")
        raise

if __name__ == "__main__":
    main() 