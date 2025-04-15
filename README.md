# Protocol Agent

A Python-based system that monitors macroeconomic and crypto market experts on Twitter, generates AI-powered summaries, and delivers daily intelligence reports via email.

## Features

- **Twitter Monitoring**: Tracks 12 key market experts for high-signal insights
- **AI Analysis**: Uses GPT-4-turbo to generate structured market intelligence
- **Email Delivery**: Sends formatted reports via Resend
- **Data Storage**: Persists tweets and summaries in Supabase

## Twitter Handles Monitored

The system tracks the following experts:
- @fejau_inc
- @DariusDale42
- @CavanXy
- @Citrini7
- @FedGuy12
- @fundstrat
- @dgt10011
- @Bluntz_Capital
- @AriDavidPaul
- @cburniske
- @qthomp
- @RaoulGMI

## AI Summary Generation

The system uses GPT-4-turbo to analyze tweets and generate structured summaries with the following sections:

🧠 Macro  
🏛️ Politics & Geopolitics  
📊 Traditional Markets  
💰 Crypto Markets  
🔄 Observed Shifts in Sentiment or Tone

Each insight includes:
- Concise, professional summary
- Twitter handle attribution
- Direct link to source tweet
- Multiple links when insights span multiple tweets

## Email Flow

Reports are delivered via Resend with:
- Clean, monospace formatting
- Structured sections with emoji headers
- Direct links to source tweets
- Timestamp of generation

## Supabase Integration

The system stores:
- Raw tweets with metadata
- Public metrics (likes, retweets, etc.)
- Generated summaries
- Processing status

## Environment Variables

Required environment variables:
```
# Twitter API
TWITTER_BEARER_TOKEN=your_twitter_bearer_token

# OpenAI
OPENAI_API_KEY=your_openai_api_key

# Resend
RESEND_API_KEY=your_resend_api_key
RESEND_FROM=your_from_email
RESEND_TO=your_to_email

# Supabase
SUPABASE_URL=your_supabase_url
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key
```

## Setup

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Create `.env` file with required variables
4. Run the script:
   ```bash
   python main.py
   ```

## Database Schema

The Supabase `messages` table includes:
- content (text)
- author (text)
- timestamp (timestamp)
- tweet_url (text)
- company (text)
- like_count (integer)
- retweet_count (integer)
- reply_count (integer)
- quote_count (integer)
- summarized (boolean)

## 🛰️ Protocol-Agent

An AI-powered monitoring and summarization agent for onchain projects and protocols. Aggregates and analyzes information from various social and analytics data sources to generate concise, high-signal updates.

## 🚀 Features

- 🐦 Twitter monitoring of selected crypto projects
- 📅 Date-based filtering of content
- 🗄️ Persistent storage in Supabase
- 🔄 Automatic deduplication
- 🤖 AI-powered summarization (coming soon)

## 🛠️ Tech Stack

- Python 3.11+
- Tweepy for Twitter API
- Supabase for storage
- Arcade.dev for AI capabilities (upcoming)
- Railway for deployment

## 📦 Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/protocol-agent.git
cd protocol-agent
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your credentials
```

## 🔑 Environment Variables

Create a `.env` file with:

```
TWITTER_BEARER_TOKEN=your_twitter_bearer_token
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
```

## 🏃‍♂️ Running the Project

```bash
python main.py
```

## 🐳 Docker Deployment

```bash
docker build -t protocol-agent .
docker run -it --env-file .env protocol-agent
```

## 📝 License

MIT

## 🤝 Contributing

Contributions welcome! Please feel free to submit a Pull Request. 