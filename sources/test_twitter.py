import os
from dotenv import load_dotenv
import tweepy

# Load environment variables
load_dotenv()
BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN")

print("🔑 Twitter Bearer Token:", BEARER_TOKEN[:10] + "..." + BEARER_TOKEN[-10:])

# Initialize Twitter client
client = tweepy.Client(bearer_token=BEARER_TOKEN)
print("🤖 Twitter client initialized")

# Try to get a user
try:
    user = client.get_user(username="qthomp")
    print(f"✅ Successfully found user: {user.data.name} (@{user.data.username})")
except Exception as e:
    print(f"❌ Error: {str(e)}") 