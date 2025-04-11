# Macro-Agent Documentation

## Overview
The Macro-Agent is a Python-based system designed to monitor, analyze, and summarize macro-focused Twitter content from key market participants. It automates the process of gathering insights from influential macro analysts and delivers them in a structured daily report.

## Purpose
- Monitor macro-focused Twitter accounts for market insights
- Aggregate and analyze tweets from key market participants
- Generate AI-powered summaries of market-relevant content
- Deliver daily reports via email to investment teams

## Core Components

### 1. Twitter Integration (`twitter.py`)
- **Purpose**: Fetches tweets from specified Twitter handles
- **Key Features**:
  - Rate limit handling with automatic retries
  - Filters for original tweets (excludes retweets and replies)
  - Handles multiple Twitter accounts in sequence
- **Configuration**:
  - Twitter Bearer Token required (via environment variable)
  - List of handles to monitor (configurable in `main.py`)

### 2. Database Integration (`supabase_client.py`)
- **Purpose**: Manages tweet storage and tracking
- **Key Features**:
  - Stores tweets in Supabase database
  - Tracks summarized status of tweets
  - Prevents duplicate tweet storage
- **Configuration**:
  - Supabase URL and Key required (via environment variables)
  - Database schema includes:
    - `messages` table with `summarized` flag
    - Timestamp tracking
    - Author and content storage

### 3. AI Analysis (`main.py`)
- **Purpose**: Generates structured summaries of collected tweets
- **Key Features**:
  - Uses OpenAI's GPT-3.5-turbo for analysis
  - Structured output format focusing on:
    - Macro insights
    - Politics & Geopolitics
    - Traditional Markets
    - Crypto Markets
  - Source attribution and linking

### 4. Email Delivery (`main.py`)
- **Purpose**: Distributes daily reports to stakeholders
- **Key Features**:
  - Uses Resend.com for email delivery
  - Structured email format
  - Includes both summary and raw tweets
- **Configuration**:
  - Sender and recipient emails (via environment variables)
  - Resend API key required

## Workflow

1. **Data Collection**
   - Script runs daily
   - Fetches tweets from configured handles
   - Saves new tweets to database
   - Handles Twitter API rate limits automatically

2. **Data Processing**
   - Queries database for non-summarized tweets
   - Filters for today's content
   - Prepares data for AI analysis

3. **Analysis**
   - Generates AI-powered summary
   - Structures content by topic
   - Extracts key insights
   - Maintains source attribution

4. **Delivery**
   - Sends email report
   - Marks processed tweets as summarized
   - Logs success/failure of each step

## Configuration Parameters

### Environment Variables Required
```bash
TWITTER_BEARER_TOKEN=your_twitter_token
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
OPENAI_API_KEY=your_openai_key
SENDER_API_KEY=your_resend_key
EMAIL_SENDER=your_sender_email
EMAIL_RECIPIENT=your_recipient_email
```

### Twitter Handles (Configurable in `main.py`)
```python
users = [
    "qthomp",
    "RaoulGMI",
    "fejau_inc",
    "DariusDale42",
    "CavanXy",
    "Citrini7",
    "FedGuy12",
    "fundstrat",
    "dgt10011",
    "Bluntz_Capital"
]
```

## Error Handling
- Twitter API rate limits: Automatic retry with 15-minute wait
- Database errors: Logged and handled gracefully
- Email failures: Logged and tweets remain unsummarized
- AI generation errors: Logged with fallback message

## Output Format
The daily report includes:
1. AI-generated summary structured by topic
2. Raw tweets with attribution
3. Timestamp of generation
4. Source links for reference

## Maintenance
- Regular monitoring of Twitter API limits
- Periodic review of handle list for relevance
- Database cleanup of old tweets (optional)
- Monitoring of email delivery success 