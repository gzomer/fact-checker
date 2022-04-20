import requests
import nltk
import json
import torch
import pymongo
import threading
import time
import hashlib

from transformers import AutoModelForSequenceClassification, AutoTokenizer
from nltk import sent_tokenize
from bs4 import BeautifulSoup
from html2text import HTML2Text

client = pymongo.MongoClient("mongodb://localhost:27017")
db = client.get_database('factchecker')

default_device = 'cpu'
interval_spotter = 5
batch_size = 2

MULTILINGUAL = True
if MULTILINGUAL:
    model_name = 'gzomer/claim-spotter-multilingual'
    tokenizer_name = 'bert-base-multilingual-cased'
else:
    model_name = 'gzomer/claim-spotter'
    tokenizer_name = 'distilbert-base-uncased'
tokenizer = AutoTokenizer.from_pretrained(tokenizer_name)
model = AutoModelForSequenceClassification.from_pretrained(model_name, num_labels=2)
model.eval()
nltk.download('punkt')

def get_prediction(text, device=default_device):
    inputs = tokenizer(text, padding=True, truncation=True, return_tensors="pt").to(device)
    outputs = model(**inputs)
    probs = outputs[0].softmax(1)
    label = int(probs.argmax().cpu().numpy())
    return model.config.id2label[label]

def get_predictions(texts, device=default_device):
    inputs = tokenizer(texts, padding=True, truncation=True, return_tensors="pt").to(device)
    with torch.no_grad():
        outputs = model(**inputs)
    probs = outputs[0].softmax(1)
    labels = [model.config.id2label[item] for item in probs.argmax(1).cpu().numpy()]
    return list(zip(texts, labels))

def get_page_content(url):
    html = requests.get(url).text
    soup = BeautifulSoup(html, 'html')
    article_element = soup.find('article')
    title_element = soup.find('title')
    text = ''
    title = ''
    if article_element:
        text = HTML2Text().handle(str(article_element))
    if title_element:
        title = title_element.text
    return text, title

def has_entities(text):
    return any(c.isupper() for c in text[1:])

def filter_sentence(sent):
    if '\n\n' in sent:
      return False
    if '[' in sent or ']' in sent:
      return False
    if '(' in sent or ')' in sent:
      return False
    if not has_entities(sent):
      return False
    if len(sent) < 20 or len(sent) > 150:
      return False
    return True

def improve_sentences(sent):
    return sent.replace('\n', ' ')

def filter_sentences(sents):
    filtered_sents = [sent for sent in sents if filter_sentence(sent)]
    filtered_sents = list(set(filtered_sents))
    filtered_sents = [improve_sentences(sent).strip() for sent in filtered_sents]
    filtered_sents = [sent for sent in filtered_sents if sent]
    return filtered_sents

def find_claims(url):
    text, title = get_page_content(url)
    sents = sent_tokenize(text)
    filtered_sents = filter_sentences(sents)
    filtered_sents += [title]
    if not filtered_sents:
        return [], 0
    preds = get_predictions(filtered_sents)
    contents = [item[0].strip() for item in preds if item[1] == 'claim']
    claims = [item for item in contents if item.strip()]
    proportion = 0
    if len(sents) > 0:
        proportion = len(claims) / len(sents)
    return claims, proportion

def process_claims():
    coll_links = db.get_collection('links')
    coll_facts = db.get_collection('facts')
    while True:
        print('Processing claims...')
        links = coll_links.find({'processed': False, 'error': False, 'graph': 'NewsFacts'}).limit(batch_size)
        for link in links:
            url = link['url']
            claims, proportion = find_claims(url)
            if not claims:
                coll_links.update_one({'_id': link['_id']}, {'$set': {'processed': True, 'facts': len(claims)}})
                continue
            # Insert Facts
            facts = []
            for claim in claims:
                data = {
                    'claim': claim,
                    'veracity': 'True',
                    'year': time.strftime("%Y"),
                }
                # sha1(claim) (string)
                unique_id = hashlib.sha1(claim.encode('utf-8')).hexdigest()

                facts.append({
                    'url': url + '#' + unique_id,
                    'data': data,
                    'source': link['source'],
                    'graph': link['graph'],
                })
            # Insert many (ignore errors)
            try:
                coll_facts.insert_many(facts, ordered=False)
            except pymongo.errors.BulkWriteError:
                pass
            # Update Link
            coll_links.update_one({'_id': link['_id']}, {'$set': {'processed': True, 'facts': len(claims)}})
            print('Extract facts from:', url, ' - total: ', len(claims), ' - claims/sentences proportion : ', round(proportion*100, 2), '%')
        time.sleep(interval_spotter)

if __name__ == '__main__':
    # Run thread to extract facts
    thread = threading.Thread(target=process_claims)
    thread.start()
