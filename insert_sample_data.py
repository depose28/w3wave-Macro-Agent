from supabase_client import SupabaseClient
from datetime import datetime, timezone

def insert_sample_data():
    client = SupabaseClient()
    
    # Sample tweets data
    sample_tweets = [
        # 0xfluid tweets
        {
            "company": "0xfluid",
            "author": "0xfluid",
            "content": "🚀 Q2 2024 Roadmap Update:\n- Layer 2 integration\n- Cross-chain bridge deployment\n- Enhanced liquidity pools\n- Mobile app beta release\nStay tuned for more details! #DeFi #Crypto",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": "twitter",
            "tweet_url": "https://twitter.com/0xfluid/status/1234567890123456789"
        },
        {
            "company": "0xfluid",
            "author": "0xfluid",
            "content": "📈 $FLUID token hits new ATH! Trading volume up 300% this week. Thanks to our amazing community for the continued support! #TokenMetrics",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": "twitter",
            "tweet_url": "https://twitter.com/0xfluid/status/1234567890123456790"
        },
        {
            "company": "0xfluid",
            "author": "0xfluid",
            "content": "🎉 Welcome @CryptoSarah as our new Head of Product! With 8 years of DeFi experience, she'll be leading our product strategy and innovation. #TeamGrowth",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": "twitter",
            "tweet_url": "https://twitter.com/0xfluid/status/1234567890123456791"
        },
        # Celestia tweets
        {
            "company": "celestia",
            "author": "celestia",
            "content": "📋 Celestia 2024 Roadmap:\n1. Data Availability Sampling v2\n2. Light Client Implementation\n3. Quantum Resistance Research\n4. Ecosystem Fund Launch\nBuilding the future of modular blockchains! 🌟",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": "twitter",
            "tweet_url": "https://twitter.com/celestia/status/1234567890123456792"
        },
        {
            "company": "celestia",
            "author": "celestia",
            "content": "📊 $TIA Market Update:\n- Listed on 3 new major exchanges\n- 24h trading volume: $150M\n- New staking rewards program launching next week\nBullish on the future! 🚀",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": "twitter",
            "tweet_url": "https://twitter.com/celestia/status/1234567890123456793"
        },
        {
            "company": "celestia",
            "author": "celestia",
            "content": "👥 Team Update: Thrilled to announce we've expanded our core dev team! 5 new senior engineers joining from @ethereum, @cosmos, and @solana. Together we're stronger! #Web3 #Hiring",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": "twitter",
            "tweet_url": "https://twitter.com/celestia/status/1234567890123456794"
        }
    ]
    
    # Insert each tweet
    for tweet in sample_tweets:
        result = client.store_tweet(tweet)
        if result:
            print(f"Successfully inserted tweet from {tweet['author']}")
        else:
            print(f"Failed to insert tweet from {tweet['author']}")

if __name__ == "__main__":
    insert_sample_data() 