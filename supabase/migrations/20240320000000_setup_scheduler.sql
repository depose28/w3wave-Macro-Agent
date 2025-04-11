-- Create a new cron job that runs at 8:00 AM CET (7:00 AM UTC) every day
INSERT INTO cron.job (
  schedule,
  command,
  database,
  active
) VALUES (
  '0 7 * * *', -- 7:00 AM UTC (8:00 AM CET)
  'SELECT net.http_post(
    url := ''https://syaeekyjwrfaqunyhwjf.supabase.co/functions/v1/macro-agent'',
    headers := jsonb_build_object(
      ''Content-Type'', ''application/json'',
      ''Authorization'', ''Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InN5YWVla3lqd3JmYXF1bnlod2pmIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDQyMTE4NDYsImV4cCI6MjA1OTc4Nzg0Nn0.NiYizkkCuKcAd3GdIfwwFV_Mpwfb5npjwxAoujubal0''
    )
  );',
  'postgres',
  true
); 