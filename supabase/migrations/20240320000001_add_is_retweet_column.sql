-- Add is_retweet column to messages table
ALTER TABLE messages
ADD COLUMN is_retweet BOOLEAN DEFAULT FALSE; 