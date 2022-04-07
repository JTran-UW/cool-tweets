import argparse
import pandas as pd
from tools.TweetParser import TweetParser
import sys

# Get tool arguments
parser = argparse.ArgumentParser()
parser.add_argument(
    "--input",
    type=str,
    help="Raw twitter input data from Twitter.py API",
    required=True
)
parser.add_argument(
    "--output",
    type=str,
    default="result.csv",
    help="Output file"
)
parser.add_argument(
    "--model",
    type=str,
    help="Model type (jtweeter1, jtweeter2)",
    required=True
)
args = parser.parse_args()

models = ["jtweeter1", "jtweeter2", "jtweeter3", "jtweeter4", "jtweeter5"]
if args.model not in models:
    sys.exit(f"Model {args.model} not found...")

raw = pd.read_csv(args.input)
raw = raw.drop(["tweet_id", "tweet_user", "tweet", "has_link", "has_photo"], axis=1) # Drop classifier features

# Merge link and photo contexts into single "context" feature
for i, row in raw.iterrows():
    link_context = row["link_context"] if not pd.isna(row["link_context"]) else ""
    photo_context = row["photo_context"] if not pd.isna(row["photo_context"]) else ""

    raw.loc[i, "context"] = link_context + photo_context
clean = raw.drop(["link_context", "photo_context"], axis=1) # Drop link and photo context features

# Get classified tweets, drop TDE (Tweet Doesn't Exist) or pd.na (hasn't been classified)
for i, row in clean.iterrows():
    mc = row["my_classification"]
    if pd.isna(mc):
        clean.drop(i, inplace=True)
    if mc == "TDE":
        clean.drop(i, inplace=True)

# Open TweetParser
tp = TweetParser()

# Normalize tokens in text and context
for i, row in clean.iterrows():
    tweet_text = tp.normalize_text(row["tweet_text"], args.model)
    clean.loc[i, "tweet_text"] = tweet_text

    if not pd.isna(row["context"]): # If row has context, normalize it
        tweet_context = tp.normalize_text(row["context"], args.model)
        clean.loc[i, "context"] = tweet_context

if args.model == "jtweeter4":
    clean.drop(["context"], axis=1, inplace=True)

clean.drop_duplicates(inplace=True)
clean.to_csv(args.output, index=False)
