from main import main
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Override some environment variables for testing
os.environ['TWITTER_WAIT_TIME'] = '10'  # Increase wait time to 10 seconds
os.environ['MAX_HANDLES'] = '5'  # Process only 5 handles at a time

if __name__ == "__main__":
    main() 