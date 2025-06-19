import os
from flask import Flask, render_template, jsonify
from flask_apscheduler import APScheduler
import requests
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from twilio.rest import Client

app = Flask(__name__)
app.config.from_mapping(
    NEWSAPI_KEY=os.getenv("NEWSAPI_KEY", ""),
    TWILIO_ACCOUNT_SID=os.getenv("TWILIO_ACCOUNT_SID", ""),
    TWILIO_AUTH_TOKEN=os.getenv("TWILIO_AUTH_TOKEN", ""),
    TWILIO_PHONE_NUMBER=os.getenv("TWILIO_PHONE_NUMBER", ""),
    USER_PHONE_NUMBER=os.getenv("USER_PHONE_NUMBER", "+917489303119")
)

scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()

analyzer = SentimentIntensityAnalyzer()
news_cache = []

def send_sms(msg):
    if app.config["TWILIO_ACCOUNT_SID"]:
        client = Client(app.config["TWILIO_ACCOUNT_SID"], app.config["TWILIO_AUTH_TOKEN"])
        client.messages.create(
            body=msg,
            from_=app.config["TWILIO_PHONE_NUMBER"],
            to=app.config["USER_PHONE_NUMBER"]
        )
    else:
        print("[SMS Placeholder]", msg)

@scheduler.task('interval', id='fetch_task', minutes=1)
def fetch_positive():
    key = app.config["NEWSAPI_KEY"]
    if not key:
        print("NEWSAPI_KEY missing.")
        return

    resp = requests.get(f"https://newsapi.org/v2/top-headlines?category=business&language=en&apiKey={key}")
    articles = resp.json().get('articles', [])
    new_headlines = []
    for art in articles:
        text = art['title'] + ". " + (art.get('description') or '')
        if analyzer.polarity_scores(text)['compound'] > 0.4:
            new_headlines.append(art['title'])
    global news_cache
    if new_headlines != [n['title'] for n in news_cache]:
        for title in new_headlines:
            send_sms(title)
    news_cache = [{'title': a['title'], 'url': a['url'], 'source': a['source']['name']} for a in articles if analyzer.polarity_scores(a['title'])['compound'] > 0.4]

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/news')
def api_news():
    return jsonify(news_cache)

if __name__ == '__main__':
    app.run()