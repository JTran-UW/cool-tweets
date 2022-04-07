import tweepy
import pandas as pd
import json
from tools.TweetParser import TweetParser
import argparse

# Get tool arguments
parser = argparse.ArgumentParser()
parser.add_argument(
    "--input",
    type=str,
    help="Existing Twitter dataset to add onto",
    required=True
)
parser.add_argument(
    "--output",
    type=str,
    default="result.csv",
    help="Output file"
)
args = parser.parse_args()

# Twitter API Keys
with open("api_keys/twitter.json") as f:
    twitter_keys = json.load(f)
consumer_key = twitter_keys["consumer_key"]
consumer_key_secret = twitter_keys["consumer_key_secret"]
access_token = twitter_keys["access_token"]
access_token_secret = twitter_keys["access_token_secret"]
bearer_token = twitter_keys["bearer_token"]

class Listener(tweepy.Stream):
    # Output df settings
    output_filename = args.output
    output = pd.read_csv(args.input, header=0)
    rows = len(output.index) # Row iterations
    row_total = 5000
    row_increment = 10
    
    # Open TweetParser
    tp = TweetParser(verbose=True)

    def on_data(self, data):
        tweet = json.loads(data)
        new_row = self.tp.parse_tweet(tweet)

        if new_row: # If tweet successfully parsed, add to database
            self.output = self.output.append(new_row, ignore_index=True)
            self.rows += 1
            print(f"Tweet passed into db")
        else:
            print(f"Tweet deemed ineligible")
        
        # If increment passed, save to csv
        if self.rows % self.row_increment == 0:
            self.output.to_csv(self.output_filename, index=False)

        # Stop script if total reached
        if self.rows == self.row_total:
            raise BaseException("We're all done here.")
     
stream = Listener(consumer_key, consumer_key_secret, access_token, access_token_secret)
stream.sample(languages=["en"])
