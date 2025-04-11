-- Add remaining retweet-related columns to messages table
ALTER TABLE messages
ADD COLUMN retweeted_by TEXT,
ADD COLUMN original_tweet_id TEXT; 