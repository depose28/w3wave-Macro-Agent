from datetime import datetime, timezone

def is_today(timestamp: datetime) -> bool:
    """Check if a timestamp is from today."""
    now = datetime.now(timezone.utc)
    return (
        timestamp.year == now.year and
        timestamp.month == now.month and
        timestamp.day == now.day
    )

def filter_tweets_by_date(tweets: list, date: datetime = None) -> list:
    """Filter tweets by date. If no date provided, returns today's tweets."""
    if not date:
        date = datetime.now(timezone.utc)
    
    return [
        tweet for tweet in tweets
        if tweet.created_at.date() == date.date()
    ] 