-- Check the current structure of the messages table
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'messages'; 