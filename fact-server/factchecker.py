import os
import requests
import re
import bs4

import openai
from tigergraph import get_tigergraph
from sentence_transformers import SentenceTransformer, util

openai.api_key = os.environ.get('OPENAI_KEY', '')
TWITTER_TOKEN = os.environ.get('TWITTER_TOKEN', '') # TODO - Replace with your token
SIMILARITY_THRESHOLD = 0.7
USE_WORKERS = os.environ.get('USE_WORKERS', True)

MULTILINGUAL = True
if MULTILINGUAL:
  model_name = 'distiluse-base-multilingual-cased-v2'
else:
  model_name = 'all-MiniLM-L6-v2'

if not USE_WORKERS:
  model = SentenceTransformer(model_name)

def find_entities(text):
  data = {
    'text': text,
    'confidence': '0.4',
    'support': '20'
  }

  response = requests.post('https://api.dbpedia-spotlight.org/en/annotate', data=data)
  return re.findall(r'<a href="(.*?)"', response.text)

def compare_claims(claim, claims):
  sentences1 = [claim]
  sentences2 = [item['claim']['text'] for item in claims]
  embeddings1 = model.encode(sentences1, convert_to_tensor=True)
  embeddings2 = model.encode(sentences2, convert_to_tensor=True)

  cosine_scores = util.cos_sim(embeddings1, embeddings2)
  claims_with_probs = list(zip(sentences2, cosine_scores[0].cpu().numpy()))
  return [
      {'claim': item[0], 'similarity': float(item[1])}
      for item in sorted(claims_with_probs, key=lambda x:x[1], reverse=True)
  ]

def rewrite_sentence(text):
  response = openai.Completion.create(
    engine="code-davinci-002",
    prompt="// Convert relation name to property comparison\nInput: John is an engineer\nRewritten: The profession of John is engineer\nInput:" +text,
    temperature=0,
    max_tokens=60,
    top_p=1,
    frequency_penalty=0,
    presence_penalty=0,
    stop=['Input']
  )
  return response.choices[0].text.replace('\nRewritten: ','').strip()

def reasoning_fact_check(claim):
    if openai.api_key == '':
      return None, 'no_openai_key'

    rewrite_claim = rewrite_sentence(claim)
    entities = find_entities(claim)
    if len(entities) == 0:
      return None, 'no_entities'
    if len(entities) != 3:
      return None, 'not_enough_entities'

    subject, predicate, object = entities
    tigergraph = get_tigergraph()
    claim_object = tigergraph.find_object_from_subject_predicate(entities[0], entities[1])
    if claim_object != entities[2]:
      return {
        'type': 'found',
        'text': f"{subject} {predicate} is not {object}",
        'truth': False,
      }, 'found'

    return None, 'cant_reason'


def fact_check(claim):
    if USE_WORKERS:
      try:
        response = requests.get('http://localhost:5003/fact_check?text=' + claim)
        data = response.json()
        if data['type'] == 'not_found':
          return None, data
        else:
          return data, data
      except Exception as e:
        return None, str(e)

    entities = find_entities(claim)
    tigergraph = get_tigergraph()
    similar_claims = tigergraph.similar_claims(entities)
    claims = similar_claims[0]['@@topMentionResults']

    sorted_claims = compare_claims(claim, claims)
    if sorted_claims:
      if sorted_claims[0]['similarity'] > SIMILARITY_THRESHOLD:
        return sorted_claims[0]['claim'], sorted_claims[0]['similarity']
      else:
        # Fallback to reasoning fact-check
        return reasoning_fact_check(claim)
    else:
        return None, 'no_claims'

def get_tweet_by_id(url):
  # Get the tweet id from url
  url = url.split('?')[0]
  tweet_id = url.split('/')[-1]
  token = TWITTER_TOKEN
  # Get full text
  response = requests.get('https://api.twitter.com/1.1/statuses/show.json?id=' + tweet_id +'&tweet_mode=extended', headers={'Authorization': 'Bearer ' + token})
  data = response.json()
  return data.get('full_text', data.get('text', ''))

def headers_and_cookies():
    # headers and cookies to prevent bot detection
    cookies = {
        '_ga': 'GA1.2.1475691555.1650372489',
        '_gid': 'GA1.2.1917206138.1650372489',
        'tmr_detect': '1%7C1650436617598',
        'tmr_reqNum': '58',
    }

    headers = {
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'accept-language': 'en-US,en;q=0.9,pt-BR;q=0.8,pt;q=0.7',
        'cache-control': 'no-cache',
        'pragma': 'no-cache',
        'sec-ch-ua': '" Not A;Brand";v="99", "Chromium";v="100", "Google Chrome";v="100"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'none',
        'sec-fetch-user': '?1',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.88 Safari/537.36',
    }
    return headers, cookies

def fact_check_by_url(url):
    # Download the page and get title
    headers, cookies = headers_and_cookies()
    page = requests.get(url, headers=headers, cookies=cookies)
    if 'twitter.com' in url:
      title = get_tweet_by_id(url)
      if not title:
        return None, 'no_title'
    else:
      soup = bs4.BeautifulSoup(page.text, 'html.parser')
      # Get the title
      title = soup.find('title')
      if not title or not title.text:
        return None, 'no_title'
      title = title.text
    return fact_check(title)