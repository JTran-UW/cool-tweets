import urllib.error
import urllib.request
import requests
from google.cloud import vision
from bs4 import BeautifulSoup
import json
from nltk.tokenize.casual import TweetTokenizer
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer
from nltk.corpus import stopwords

# SightEngine API Keys
with open("api_keys/sightengine.json") as f:
    se_keys = json.load(f)
se_user_key = se_keys["se_user_key"]
se_secret_key = se_keys["se_secret_key"]

class TweetParser:
    # Link summary session
    session = requests.Session()

    # Tweet tokenizer
    twtokenizer = TweetTokenizer()

    # API Clients
    vision_client = vision.ImageAnnotatorClient()
    se_data = {
        "mode": "standard",
        "lang": "en",
        "api_user": se_user_key,
        "api_secret": se_secret_key
    }

    # Text normalization tools (stopwords, lemmatizer)
    stop_words = set(stopwords.words("english"))
    lemmatizer = WordNetLemmatizer()

    def __init__(self, verbose=False):
        self.verbose = verbose # Whether to print milestones (for debugging)

    def parse_tweet(self, tweet):
        """
        Parse a tweet for its content and context

        :param tweet: tweet object to parse
        :returns: row to append to dataframe if eligible, else None
        """
        # Get tweet fields
        extended = tweet.get("extended_tweet")
        if not extended:
            tweet_text = tweet.get("text")
            context_input = tweet
        else:
            tweet_text = extended.get("full_text")
            context_input = tweet.get("extended_tweet")
        tweet_contexts = self.get_contexts(context_input)
        tweet_id = tweet.get("id_str")
        tweet_user = tweet.get("user").get("screen_name")

        if self.verbose:
            print(tweet_text)

        eligible = self.tweet_eligible(tweet, tweet_text, tweet_contexts)
        if eligible:
            # CONTEXT: Essential tweet info not found in the text, for example an attached link or photo
            # Set up contexts
            link_context = None
            photo_context = None

            # If link in tweet, get link metadata
            if tweet_contexts["has_link"]:
                link_context = list()

                for link in self.get_all_links(tweet):
                    try:
                        meta_vals = self.get_link_meta(link) # Title and description tag content
                        title = meta_vals["title"]
                        description = meta_vals["description"]
                        
                        # If a title or a description, append to context
                        if title:
                            link_context.append(title)
                        if description:
                            link_context.append(description)
                    except requests.exceptions.ConnectTimeout:
                        if self.verbose:
                            print("Link could not be reached")
                
                # Join link contexts together with whitespace
                if len(link_context) > 0:
                    link_context = " ".join(link_context)
            
            # If photo in tweet, classify items in photo
            if tweet_contexts["has_photo"]:
                for photo_url in self.get_all_photo_urls(context_input):
                    # Classify objects in photo
                    photo_context = [obj.description for obj in self.classify_photo(photo_url)]
                    photo_context = " ".join(photo_context) # Put photo annotations into string

            # Append to dataframe
            return {
                "tweet_text": tweet_text, 
                "tweet_id": tweet_id,
                "tweet_user": tweet_user,
                "has_link": tweet_contexts["has_link"],
                "link_context": link_context,
                "has_photo": tweet_contexts["has_photo"],
                "photo_context": photo_context,
                "tweet": tweet
            }

    def tweet_eligible(self, tweet, tweet_text, tweet_context):
        """
        Determines if tweet is eligible for classification: cannot be reply, qrt, rt, or have a video

        :param tweet: tweet as dict
        :param tweet_text: full text of tweet
        :param has_video: bool if tweet has a video
        :returns: bool, true if eligible
        """
        # Check if tweet is eligible
        is_reply = tweet.get("in_reply_to_status_id") != None
        is_quote_status = tweet.get("is_quote_status")
        is_retweet = tweet.get("retweeted") or tweet.get("text")[:4] == "RT @"
        is_inappropriate = self.check_inappropriate(tweet_text)
        has_video = tweet_context["has_video"]

        return not (is_reply or is_quote_status or is_retweet or has_video or is_inappropriate or has_video)
    
    def check_inappropriate(self, tweet_text):
        """
        Query SightEngine API to check if tweet text is inappropriate

        :param tweet_text: text of tweet
        :returns: bool, true if profanity found
        """
        self.se_data["text"] = tweet_text
        se_response = requests.post("https://api.sightengine.com/1.0/text/check.json", data=self.se_data)
        se_response = json.loads(se_response.text)

        # Check for profanity
        profanity = se_response.get("profanity")
        if profanity:
            if len(profanity.get("matches")) > 0:
                return True
        return False
    
    def get_contexts(self, tweet):
        """
        Check if certain 'context' items are present in tweet: link, photo, or video

        :param tweet: tweet object to parse
        :returns: dict object of bools indicating item presence
        """
        entities = tweet.get("entities")
        extended_entities = tweet.get("extended_entities")

        # Check for relevant criteria
        has_link = len(entities.get("urls")) > 0
        has_media = extended_entities.get("media") if extended_entities else False
        has_photo = False
        has_video = False

        # If media exists in tweet, check if photos/videos
        if has_media:
            for media in has_media:
                media_type = media.get("type")
                has_photo = has_photo or media_type == "photo"
                has_video = has_video or media_type == "video"
        
        return {
            "has_link": has_link,
            "has_photo": has_photo,
            "has_video": has_video
        }

    def classify_photo(self, photo_url):
        """
        Retrieve and classify objects in photo with Vision API

        :param photo_url: url of photo
        :returns: list of annotations
        """
        try:
            content = urllib.request.urlopen(photo_url).read() # Get image from photo url
            image = vision.Image(content=content)

            # Annotate image and return annotations
            response = self.vision_client.label_detection(image=image)
            labels = response.label_annotations
        except urllib.error.HTTPError: # If image is not found
            if self.verbose:
                print("Image is not found...")
            labels = []

        return labels
    
    def get_link_meta(self, url):
        """
        Get title and description meta tags from a link

        :param url: url as string
        :returns: dict containing "title" and "description"
        """
        site = self.session.get(url, timeout=20).text
        soup = BeautifulSoup(site, features="html.parser")

        # Look for meta tags
        title_tag = soup.find("meta", attrs={"name": "twitter:title"})
        description_tag = soup.find("meta", attrs={"name": "twitter:description"})
        
        # Sometimes title and description meta tags are hidden differently
        if not title_tag:
            title_tag = soup.find("meta", property="og:title")
            description_tag = soup.find("meta", property="og:description")

        # Get content of meta tags
        try:
            title = title_tag["content"] if title_tag else None
            description = description_tag["content"] if description_tag else None
        except KeyError:
            # Sometimes they don't have any content?
            title = None
            description = None

        # Return content
        return {
            "title": title,
            "description": description
        }
    
    def get_all_links(self, tweet):
        """
        Generator function to get all link urls

        :param tweet: tweet object to parse
        """
        for url in tweet.get("entities").get("urls"):
            yield url.get("expanded_url")
    
    def get_all_photo_urls(self, tweet):
        """
        Generator function to get all tweet photos urls

        :param tweet: tweet object to parse
        """
        for media in tweet.get("entities").get("media"):
            if media["type"] == "photo":
                yield media["media_url_https"]
    
    def normalize_text(self, text, model):
        """
        Normalize/tokenize tweet text

        :param text: tweet text
        :param model: jtweeter model (jtweeter1, jtweeter2)
        :returns: whitespace delimited tokens from tweet text
        """
        tokens = []
        text = text.lower() # Set to lower case
        text = text.replace("&amp;", "") # Remove ampersand
        text = text.replace("|", "") # Remove bar
        text = text.replace(":", "") # Remove colon
        text = text.replace("-", "") # Remove hyphen
        text = text.replace(",", "") # Remove commas

        if model in ["jtweeter4", "jtweeter5"]:
            text = text.replace(".", "") # Remove periods

        # Tokenize text
        if model in ["jtweeter4", "jtweeter5"]:
            tokenlist = self.twtokenizer.tokenize(text)
        else:
            tokenlist = word_tokenize(text) # Split on whitespace

        for token in tokenlist:
            # Lemmatize if model is jtweeter2
            if model == "jtweeter2":
                token = self.lemmatizer.lemmatize(token)
            
            is_not_link = not token[:4] == "http" and not token[:6] == "//t.co"
            is_not_stopword = token not in self.stop_words

            if is_not_link and is_not_stopword:
                tokens.append(token)
        
        return " ".join(tokens)
