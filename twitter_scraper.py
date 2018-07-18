import re
from requests_html import HTMLSession, HTML
from datetime import datetime

session = HTMLSession()


def get_tweets(query_raw, pages=25):

    """Gets tweets for a given user, via the Twitter frontend API."""

    if type(query_raw)==list:
        query = '%20%2B%20'.join(['%23'+''.join(e for e in word.lower() if e.isalnum()) for word in query_raw])
    else:
        query = '%23'+''.join(e for e in query_raw.lower() if e.isalnum())

    url =  f"https://twitter.com/i/search/timeline?vertical=default&q={query}&src=typd&include_available_features=1&include_entities=1&&reset_error_state=false"

    # Url for users should we want to reinclude it
    #url = f'https://twitter.com/i/profiles/show/{user}/timeline/tweets?include_available_features=1&include_entities=1&include_new_items_bar=true'

    headers = {
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Referer': f'https://twitter.com/search?q={query}&src=typd',
        #'Referer': f'https://twitter.com/{user}',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/603.3.8 (KHTML, like Gecko) Version/10.1.2 Safari/603.3.8',
        'X-Twitter-Active-User': 'yes',
        'X-Requested-With': 'XMLHttpRequest'
    }

    def gen_tweets(pages):
        r = session.get(url, headers=headers)

        while pages > 0:
            try:
                html = HTML(html=r.json()['items_html'],
                            url='bunk', default_encoding='utf-8')
            except KeyError:
                raise ValueError(
                    f'Oops! Either "{query}" does not exist or is private.')

            comma = ","
            dot = "."
            tweets = []
            for tweet in html.find('.stream-item'):
                text = tweet.find('.tweet-text')[0].full_text
                tweetId = tweet.find(
                    '.js-permalink')[0].attrs['data-conversation-id']
                time = datetime.fromtimestamp(
                    int(tweet.find('._timestamp')[0].attrs['data-time-ms'])/1000.0)
                interactions = [x.text for x in tweet.find(
                    '.ProfileTweet-actionCount')]
                replies = int(interactions[0].split(" ")[0].replace(comma, "").replace(dot,""))
                retweets = int(interactions[1].split(" ")[
                               0].replace(comma, "").replace(dot,""))
                likes = int(interactions[2].split(" ")[0].replace(comma, "").replace(dot,""))
                hashtags = [hashtag_node.full_text for hashtag_node in tweet.find('.twitter-hashtag')]
                urls = [url_node.attrs['data-expanded-url'] for url_node in tweet.find('a.twitter-timeline-link:not(.u-hidden)') if 'data-expanded-url' in url_node.attrs]
                photos = [photo_node.attrs['data-image-url'] for photo_node in tweet.find('.AdaptiveMedia-photoContainer')]
                
                videos = []
                video_nodes = tweet.find(".PlayableMedia-player")
                for node in video_nodes:
                    styles = node.attrs['style'].split()
                    for style in styles:
                        if style.startswith('background'):
                            tmp = style.split('/')[-1]
                            video_id = tmp[:tmp.index('.jpg')]
                            videos.append({'id': video_id})
                tweets.append({'tweetId': tweetId, 'time': time, 'text': text,
                               'replies': replies, 'retweets': retweets, 'likes': likes, 
                                'hashtags': hashtags, 'urls': urls,
                                'photos': photos, 'videos': videos,
                                'search_text': query
                               })

            last_tweet = html.find('.stream-item')[-1].attrs['data-item-id']

            for tweet in tweets:
                if tweet:
                    tweet['text'] = re.sub('http', ' http', tweet['text'], 1)
                    yield tweet

            r = session.get(
                url, params = {'max_position': last_tweet}, headers = headers)
            pages += -1

    yield from gen_tweets(pages)
