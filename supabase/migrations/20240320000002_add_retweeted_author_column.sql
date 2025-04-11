-- Add retweeted_author column to messages table
ALTER TABLE messages
ADD COLUMN retweeted_author TEXT; 