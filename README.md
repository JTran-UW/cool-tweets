# Cool Tweets

## Overview
Cool Tweets was a fun final project I made for Computer Science IV. The concept was to create a machine learning model that could classify whether a tweet was "Cool" or "Not My Cup Of Tea" based upon the text and context (photos and urls).

## Quickstart
This project is currently not working, bc I am not paying for that Sagemaker domain right now. requires Python3.

Clone the project via git:

```git clone https://github.com/ProfJAT/cool-tweets.git```

Install necessary libraries:

```pip install -r requirements.txt```

Run Flask app

```runflask.cmd```

Visit project via 127.0.0.1:5000, classify app at 127.0.0.1/classify?row_id={row_id}

## How It Was Made
I created an internal tool called "classify" to create the training datasets. Around 1,422 tweets were classified! What a headache.
![2022-04-06 (3)](https://user-images.githubusercontent.com/46096425/162133012-e1810420-5a3b-4f05-a921-ad357c31167b.png)

Using AWS Sagemaker, Lambda, and API Gateway, I set up a model with ~65% accuracy and deployed it.
![2022-04-06 (1)](https://user-images.githubusercontent.com/46096425/162133055-cae2b19f-421a-4834-99e3-bad403dc4774.png)

I then created a web app in Flask and JS that allowed users to query the endpoint in realtime, or by inputting a tweet URL.
![2022-04-06 (2)](https://user-images.githubusercontent.com/46096425/162133087-e0c2ddb6-751f-4c03-8171-24010d8047e3.png)
![2022-04-06](https://user-images.githubusercontent.com/46096425/162133107-37897d45-8852-423d-a40f-8f6daaad791d.png)
