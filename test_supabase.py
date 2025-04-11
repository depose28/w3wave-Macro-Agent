from supabase_client import SupabaseClient
import os
from dotenv import load_dotenv

def test_supabase_connection():
    # Initialize the client
    client = SupabaseClient()
    
    try:
        # Try to get the count of messages
        response = client.client.table("messages").select("id", count="exact").execute()
        print("✅ Successfully connected to Supabase!")
        print(f"Total messages in database: {response.count}")
        
        # Try to insert a test message
        test_data = {
            "company": "test_company",
            "author": "test_author",
            "content": "This is a test message",
            "timestamp": "2024-01-01T00:00:00Z",
            "source": "test"
        }
        
        insert_response = client.client.table("messages").insert(test_data).execute()
        print("✅ Successfully inserted test message!")
        
        # Clean up: delete the test message
        client.client.table("messages").delete().eq("company", "test_company").execute()
        print("✅ Successfully cleaned up test message!")
        
    except Exception as e:
        print(f"❌ Error connecting to Supabase: {e}")

if __name__ == "__main__":
    test_supabase_connection() 