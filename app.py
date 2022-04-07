from flask import Flask, render_template, request
from flask_mysqldb import MySQL
import MySQLdb.cursors
import json
import tweepy
import tweepy.errors
import pandas as pd
from tools.TweetParser import TweetParser
import requests
from datetime import datetime
app = Flask(__name__)

with open("api_keys/mysql.json", "r") as login:
    sqllogin = json.load(login)

# Authenticate with MySQL user db
app.config["MYSQL_HOST"] = sqllogin.get("host")
app.config["MYSQL_USER"] = sqllogin.get("user")
app.config["MYSQL_PASSWORD"] = sqllogin.get("password")
app.config["MYSQL_DB"] = sqllogin.get("db")
mysql = MySQL(app)

# Import Tweepy API
with open("api_keys/twitter.json") as f:
    twitter_keys = json.load(f)
consumer_key = twitter_keys["consumer_key"]
consumer_key_secret = twitter_keys["consumer_key_secret"]
access_token = twitter_keys["access_token"]
access_token_secret = twitter_keys["access_token_secret"]
bearer_token = twitter_keys["bearer_token"]

auth = tweepy.OAuthHandler(consumer_key, consumer_key_secret)
auth.set_access_token(access_token, access_token_secret)
tweepy_api = tweepy.API(auth)

# Which model to normalize tweets with??
model = "jtweeter1"

# Open a TweetParser
tp = TweetParser()

def predict_tweet(parsed_tweet):
    """
    Get prediction from Sagemaker

    :param parsed_tweet: tweet object parsed by TweetParser
    :return: string result from sagemaker endpoint
    """
    data = {}
    data["tweet_text"] = tp.normalize_text(parsed_tweet["tweet_text"], model)
    
    # Merge link and photo contexts into single context variable
    context = []
    link_context = parsed_tweet["link_context"]
    photo_context = parsed_tweet["photo_context"]

    # Join all contexts into one variable
    if link_context:
        context.append(link_context)
    if photo_context:
        context.append(photo_context)
    data["context"] = " ".join(context)

    # Call to sagemaker
    prediction = requests.post("https://35553kme10.execute-api.us-east-1.amazonaws.com/jtweeter5-prod/predict-tweets", data=json.dumps(data)).text
    print(prediction)
    return prediction

def count_classification(classification, tweets):
    """
    Count how many times a certain classification is in database

    :param classification: classification to look for
    :param tweets: all tweets gotten from database
    :returns: dict, all_time is total, today is how many were classified today
    """
    all_time = 0
    today = 0

    for tweet in tweets:
        if tweet["classification"] == classification:
            all_time += 1

            if tweet["date_classified"].date() == datetime.today().date():
                today += 1
    
    return {
        "all_time": all_time,
        "today": today
    }

@app.route("/", methods=["GET", "POST"])
def home():
    errors = []

    # Create cursor
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Analyze a tweet
    if request.method == "POST":
        tweet_link = request.form.get("link")
        try:
            tweet_id = tweet_link.split("/")[-1]
            tweet = tweepy_api.get_status(tweet_id)._json
            parsed_tweet = tp.parse_tweet(tweet)

            # If tweet is eligible, classify it
            if parsed_tweet:
                user = parsed_tweet["tweet_user"]
                text = parsed_tweet["tweet_text"]
                classification = eval(predict_tweet(parsed_tweet)).split(",")[0]
            # If tweet is ineligible, give it CND (Could Not Determine)
            else:
                tweet_id = tweet["id"]
                user = tweet["user"]["screen_name"]
                text = tweet["text"]
                classification = "CND"
            
            # Check if tweet in db
            cursor.execute("SELECT * FROM joshuatran_analyzedtweets WHERE tweet_id=%s", (tweet_id,))
            tweet_in_db = cursor.fetchone()

            if tweet_in_db: # Update row with classification
                cursor.execute("""UPDATE joshuatran_analyzedtweets
                                SET classification=%s,
                                    date_classified=%s
                                WHERE tweet_id=%s
                                """, (classification, datetime.today(), tweet_id,))
                mysql.connection.commit()
            else: # Insert classification into db
                cursor.execute("INSERT INTO joshuatran_analyzedtweets VALUES (NULL, %s, %s, %s, %s, DEFAULT)", (tweet_id, user, text, classification, ))
                mysql.connection.commit()

        # IF tweet could not be found, throw error
        except tweepy.errors.NotFound:
            errors.append("Invalid link")

    # Get all classified tweets
    cursor.execute("SELECT * FROM joshuatran_analyzedtweets")
    mysql.connection.commit()
    analyzed_tweets = cursor.fetchall()

    # Get the number of times each classification has been found
    class_counts = []
    for classification in ["C", "NMCOT", "CND"]:
        counts = count_classification(classification, analyzed_tweets)
        class_counts.append({
            "name": classification,
            "all_time": counts["all_time"],
            "today": counts["today"]
        })

    return render_template("index.html", errors=errors, 
                                        tweets=analyzed_tweets, 
                                        class_counts = class_counts)

@app.route("/classifyTweet", methods=["POST"])
def classifyTweet():
    # This is for the AJAX workshop
    tweet = request.data.decode()
    normalized = tp.normalize_text(tweet, model)
    data = {
        "tweet_text": normalized,
        "context": ""
    }
    prediction = requests.post(
        "https://35553kme10.execute-api.us-east-1.amazonaws.com/jtweeter5-prod/predict-tweets", 
        data=json.dumps(data)).text # Redundant... there's a better way to do this
    print(prediction)
    return prediction

# CLASSIFY IS AN INTERNAL TOOL FOR ME TO CREATE DATASETS

# Classification datasets
raw_filename = "data/result.csv"
classified_filename = "data/result.csv"
df = pd.read_csv(raw_filename)

@app.route("/classify", methods=["GET", "POST"])
def classify():
    row_id = int(request.args.get("row_id"))

    # Add classification into dataframe, and save to filename
    if request.method == "POST":
        df.loc[row_id, "my_classification"] = request.form.get("classification")
        df.to_csv(classified_filename, index=False)
        row_id += 1

    tweet = df.iloc[row_id].to_dict()
    tweet["row_id"] = row_id

    return render_template("classify.html", tweet=tweet)
