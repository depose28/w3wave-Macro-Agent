# Macro Twitter Agent

A Python application that fetches tweets from selected accounts, generates AI summaries, and sends daily email reports.

## Setup on Replit

1. Fork this repository to your GitHub account
2. Create a new Replit project and import your forked repository
3. Set up the required environment variables in Replit:
   - Click on "Tools" in the left sidebar
   - Select "Secrets"
   - Add the following secrets:
     - `TWITTER_BEARER_TOKEN`: Your Twitter API bearer token
     - `SUPABASE_URL`: Your Supabase project URL
     - `SUPABASE_SERVICE_ROLE_KEY`: Your Supabase service role key
     - `OPENAI_API_KEY`: Your OpenAI API key
     - `SENDER_API_KEY`: Your Resend API key
     - `FROM_EMAIL`: The email address to send from
     - `TO_EMAIL`: The email address to send to
     - `MIN_ENGAGEMENT`: (Optional) Minimum engagement threshold for tweets (default: 50)

4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

5. Run the application:
   ```bash
   python main.py
   ```

## Features

- Fetches tweets from selected Twitter accounts
- Generates AI summaries using OpenAI's GPT-4
- Sends daily email reports with HTML and plain text versions
- Tracks tweet engagement metrics
- Prevents duplicate tweets in reports
- Supports custom engagement thresholds

## Configuration

You can modify the following in `main.py`:

- Twitter accounts to monitor (in the `users` list)
- Minimum engagement threshold (in `filter_and_sort_tweets`)
- Email formatting and styling
- AI summary prompt and parameters

## Development

To run tests:
```bash
python -m pytest test_*.py
```

To reset today's summarized status (for testing):
```bash
python main.py --reset-summarized
```

## License

MIT License

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