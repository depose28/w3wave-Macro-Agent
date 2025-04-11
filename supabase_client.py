from supabase import create_client
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Dict

load_dotenv()

class SupabaseClient:
    def __init__(self):
        self.url = os.getenv("SUPABASE_URL")
        self.key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        if not self.key:
            raise ValueError("SUPABASE_SERVICE_ROLE_KEY environment variable is not set")
        self.client = create_client(self.url, self.key)

    def store_tweet(self, tweet_data: dict) -> dict:
        """Store a tweet in Supabase with metadata."""
        try:
            # Remove @ symbol if present in author name
            author = tweet_data["author"].replace("@", "") if tweet_data["author"].startswith("@") else tweet_data["author"]
            
            response = self.client.table("messages").insert({
                "company": tweet_data["company"],  # Project/protocol identifier
                "author": author,
                "content": tweet_data["content"],
                "timestamp": tweet_data["timestamp"],
                "source": "twitter",
                "tweet_url": tweet_data.get("tweet_url", ""),
                "like_count": tweet_data.get("like_count", 0),
                "retweet_count": tweet_data.get("retweet_count", 0),
                "reply_count": tweet_data.get("reply_count", 0),
                "quote_count": tweet_data.get("quote_count", 0)
            }).execute()
            return response.data
        except Exception as e:
            print(f"Error storing tweet: {e}")
            return None

    def get_tweets_by_date(self, date: datetime = None, company: str = None) -> list:
        """Get tweets from a specific date.
        
        Args:
            date: datetime object for the date to fetch tweets from
            company: optional company filter
        
        Returns:
            List of tweet dictionaries
        """
        try:
            # Build the query
            query = self.client.table("messages").select("*")
            
            # Add date filter
            if date:
                next_day = date + timedelta(days=1)
                query = query.gte("timestamp", date.isoformat()).lt("timestamp", next_day.isoformat())
            
            # Add company filter if provided
            if company:
                query = query.eq("company", company)
            
            # Only get non-summarized tweets
            query = query.eq("summarized", False)
            
            # Execute query
            response = query.execute()
            return response.data
            
        except Exception as e:
            print(f"Error fetching tweets: {e}")
            return []

    def is_tweet_exists(self, author: str, content: str) -> bool:
        """Check if a tweet with the given author and content already exists."""
        try:
            # Remove @ symbol if present in author name
            author = author.replace("@", "") if author.startswith("@") else author
            
            response = self.client.table("messages")\
                .select("id")\
                .eq("author", author)\
                .eq("content", content)\
                .eq("source", "twitter")\
                .execute()
            return len(response.data) > 0
        except Exception as e:
            print(f"Error checking tweet existence: {e}")
            return False

    def mark_tweets_as_summarized(self, tweet_ids: List[str]) -> bool:
        """Mark tweets as summarized in the database.
        
        Args:
            tweet_ids: List of tweet IDs to mark as summarized
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            response = self.client.table("messages")\
                .update({"summarized": True})\
                .in_("id", tweet_ids)\
                .execute()
            return True
        except Exception as e:
            print(f"Error marking tweets as summarized: {e}")
            return False

    def store_fluid_metrics(self, metrics_data: Dict) -> Dict:
        """Store Fluid metrics in Supabase."""
        try:
            # Check if we already have data for this date range
            existing_data = self.client.table("fluid_metrics") \
                .select("*") \
                .eq("start_date", metrics_data["start_date"]) \
                .eq("end_date", metrics_data["end_date"]) \
                .execute()
            
            if existing_data.data:
                print(f"📊 Data already exists for {metrics_data['start_date']} to {metrics_data['end_date']}")
                return existing_data.data[0]
            
            # Add covered flag to new data
            metrics_data["covered"] = False
            
            # Insert new metrics data
            result = self.client.table("fluid_metrics") \
                .insert(metrics_data) \
                .execute()
            
            print("✅ Successfully saved metrics to Supabase")
            return result.data[0]
        except Exception as e:
            print(f"❌ Error storing metrics: {e}")
            raise

    def get_latest_fluid_metrics(self) -> Optional[dict]:
        """Get the most recent Fluid metrics from Supabase.
        
        Returns:
            dict: The most recent metrics data if found, None otherwise
        """
        try:
            response = self.client.table("fluid_metrics")\
                .select("*")\
                .order("created_at", desc=True)\
                .limit(1)\
                .execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"Error fetching latest Fluid metrics: {e}")
            return None

    def mark_metrics_as_covered(self, metrics_id: str) -> Dict:
        """Mark metrics data as covered in Supabase."""
        try:
            result = self.client.table("fluid_metrics") \
                .update({"covered": True}) \
                .eq("id", metrics_id) \
                .execute()
            
            print(f"✅ Successfully marked metrics {metrics_id} as covered")
            return result.data[0]
        except Exception as e:
            print(f"❌ Error marking metrics as covered: {e}")
            raise

    def get_messages_by_date_range(self, start_date: str, end_date: str, company: str = "fluid") -> List[Dict]:
        """Get messages from Supabase within a date range.
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            company: Company/project identifier (default: "fluid")
            
        Returns:
            List of message dictionaries
        """
        try:
            # Convert string dates to datetime objects
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)  # Include the end date
            
            # Build the query
            response = self.client.table("messages") \
                .select("*") \
                .eq("company", company) \
                .gte("timestamp", start_dt.isoformat()) \
                .lt("timestamp", end_dt.isoformat()) \
                .order("timestamp", desc=True) \
                .execute()
            
            return response.data
        except Exception as e:
            print(f"Error fetching messages by date range: {e}")
            return []

    def store_ai_report(self, report_data: dict) -> dict:
        """Store an AI-generated report in Supabase.
        
        Args:
            report_data: Dictionary containing:
                - summary: The AI-generated summary
                - tweet_ids: List of tweet IDs included in the report
                - date: Date of the report
                - email_sent: Boolean indicating if email was sent
        
        Returns:
            dict: The stored report data if successful, None otherwise
        """
        try:
            response = self.client.table("ai_reports").insert({
                "summary": report_data["summary"],
                "tweet_ids": report_data["tweet_ids"],
                "date": report_data["date"],
                "email_sent": report_data.get("email_sent", False)
            }).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"Error storing AI report: {e}")
            return None

    def get_ai_report_by_date(self, date: datetime) -> Optional[dict]:
        """Get an AI report for a specific date.
        
        Args:
            date: datetime object for the date to fetch report from
        
        Returns:
            dict: The report data if found, None otherwise
        """
        try:
            response = self.client.table("ai_reports")\
                .select("*")\
                .eq("date", date.date().isoformat())\
                .execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"Error fetching AI report: {e}")
            return None 