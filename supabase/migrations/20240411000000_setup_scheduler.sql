-- Create a function to handle the scheduled task
CREATE OR REPLACE FUNCTION public.handle_daily_macro_update()
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    -- Call the Edge Function
    PERFORM net.http_post(
        url := 'https://syaeekyjwrfaqunyhwjf.supabase.co/functions/v1/macro-agent',
        headers := jsonb_build_object(
            'Authorization', 'Bearer ' || current_setting('app.settings.service_role_key', true),
            'Content-Type', 'application/json'
        )
    );
END;
$$;

-- Create the cron job
SELECT cron.schedule(
    'daily-macro-update',
    '0 9 * * *',  -- Run at 9:00 AM every day
    $$
    SELECT handle_daily_macro_update();
    $$
); 