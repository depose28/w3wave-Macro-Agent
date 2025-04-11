-- Add original_tweet_id column to messages table
ALTER TABLE messages
ADD COLUMN original_tweet_id TEXT; 