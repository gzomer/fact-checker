import threading
import pymongo
import requests
import time
import json
import os
from tigergraph import TigerGraph

tigergraph = {
    'FactChecking': None,
    'NewsFacts': None,
}
client = pymongo.MongoClient("mongodb://localhost:27017")
db = client.get_database('factchecker')

FACT_CHECKING_GRAPH = 'FactChecking'
NEWS_FACTS_GRAPH = 'NewsFacts'
DEFAULT_GRAPH = FACT_CHECKING_GRAPH

STATE_FOLDER = './state/'

# Batch size
import_batch_size = 5
extract_batch_size = 5

# Time interval between each batch
extract_interval = 5
import_interval = 5
ping_interval = 30

def find_entities(text):
  data = {
    'text': text,
    'confidence': '0.4',
    'support': '20'
  }

  response = requests.post('https://api.dbpedia-spotlight.org/en/annotate', data=data)
  return response.json()

def extract_entities():
    collection = db.get_collection('facts')
    veracity_filter = [
        'True', 'False', 'true', 'false'
    ]
    while True:
        print('Extracting entities...')
        try:
            # Get a random fact (return only id and data.claim)
            facts = collection.find({
                'data.entities': {'$exists': False},
                'data.veracity': {'$in': veracity_filter}
                }, {'_id': 1, 'data': 1}
            ).limit(extract_batch_size)
            count = 0
            for fact in facts:
                entities = find_entities(fact['data']['claim'])
                collection.update_one({'_id': fact['_id']}, {'$set': {'data.entities': entities}})
                count += 1
            print('Extracted {} entities'.format(count))

        except Exception as e:
            print('Extract error', e)

        time.sleep(extract_interval)


def get_next_id(state, type, value=None):
    if type == 'claim' or type == 'source':
        if type not in state:
            state[type] = 1
        else:
            state[type] += 1
        return state[type], True
    elif type == 'mention':
        is_new = False
        if value is None:
            raise Exception('Value is required')
        if type not in state:
            state[type] = {
                'next': 1,
                'data': {}
            }

        if value in state[type]['data']:
            return state[type]['data'][value], False
        else:
            state[type]['data'][value] = state[type]['next']
            state[type]['next'] += 1
            is_new = True
            return state[type]['data'][value], is_new
    raise Exception('Invalid type')

def parse_veracity(veracity):
    veracity = veracity.lower()
    if veracity == 'true':
        return True
    elif veracity == 'false':
        return False
    else:
        return None

def parse_entities(entities):
    if 'Resources' not in entities:
        return None
    return [{
        'name': entity['@surfaceForm'],
        'url': entity['@URI'].replace('http://dbpedia.org/resource/', '').replace('https://dbpedia.org/resource/', '')
    } for entity in entities['Resources']]


def escape_text(text):
    # Escape double quotes
    text = text.replace('"', "'")
    return text

def has_imported(state, fact):
    if 'imported' not in state:
        return False
    if str(fact['_id']) not in state['imported']:
        return False
    return True

def generate_ids(state, facts):
    claims = []
    mentions = []
    claims_mentions = []
    sources = []
    claims_sources = []
    imported_status = {}

    for fact in facts:
        if has_imported(state, fact):
            imported_status[fact['_id']] = 'success'
            continue
        imported_status[fact['_id']] = 'not_imported'
        try:
            fact_data = fact['data']
            veracity = parse_veracity(fact_data['veracity'])
            if veracity is None:
                imported_status[fact['_id']] = 'invalid_veracity'
                continue
            # Generate claim id
            claim_id, is_new = get_next_id(state, 'claim')
            claims.append({
                'id': claim_id,
                'text': escape_text(fact_data['claim']),
                'year': fact_data.get('year', time.strftime('%Y')),
                'is_true': veracity,
            })

            # Generate sources
            source = fact['source']
            source_url = fact['url']
            source_id, is_new = get_next_id(state, 'source', value=source)
            # If exists, no need to reimport
            if is_new:
                sources.append({
                    'id': source_id,
                    'name': source,
                    'url': source_url,
                })

            claims_sources.append({
                'claim_id': claim_id,
                'source_id': source_id
            })

            # Generate mentions
            entities = parse_entities(fact_data['entities'])
            if not entities:
                imported_status[fact['_id']] = 'no_entities'
                continue

            for entity in entities:
                mention_id, is_new = get_next_id(state, 'mention', value=entity['url'])
                if is_new:
                    mentions.append({
                        'id': mention_id,
                        'name': entity['name'],
                        'entity_type': entity['url'],
                    })

                claims_mentions.append({
                    'claim': claim_id,
                    'mention': mention_id
                })
            imported_status[fact['_id']] = 'success'
        except Exception as e:
            print('Generate error', e)
            imported_status[fact['_id']] = 'error'

    return claims, mentions, claims_mentions, sources, claims_sources, imported_status

def import_facts():
    global all_states
    collection = db.get_collection('facts')
    current_graph = DEFAULT_GRAPH

    state = all_states[current_graph]
    while True:
        print('Importing facts...')
        # Cycle graph
        if current_graph == FACT_CHECKING_GRAPH:
            current_graph = NEWS_FACTS_GRAPH
        else:
            current_graph = FACT_CHECKING_GRAPH

        try:
            facts = collection.find({
                'data.entities': {'$exists': True},
                'imported': {'$exists': False},
                'graph': current_graph,
            }).limit(import_batch_size)

            claims, mentions, claims_mentions, sources, claims_sources, imported_status = generate_ids(state, facts)

            if not claims:
                print('Waiting...')
                time.sleep(import_batch_size)
                continue
            try:
                run_import_jobs(current_graph, claims, mentions, claims_mentions, sources, claims_sources)
                # Update imported state
                if 'imported' not in state:
                    state['imported'] = {}
                for fact_id in imported_status:
                    if imported_status[fact_id] == 'success':
                        state['imported'][str(fact_id)] = True
            except Exception as e:
                print('Import error', e)
                print('==> Trying again later')
                time.sleep(import_interval * 5)
                continue

            # Update facts with imported status
            for fact_id, status in imported_status.items():
                collection.update_one({'_id': fact_id}, {'$set': {'imported': status}})

            all_states[current_graph] = state
            save_state(current_graph)
        except Exception as e:
            print('Import error', e)

        time.sleep(import_interval)

def load_state():
    global all_states
    all_states = {
        'FactChecking': {},
        'NewsFacts': {},
    }

    # Load state dict from state (if exists)
    for key in all_states:
        if os.path.exists(f'{STATE_FOLDER}/{key}.json'):
            with open(f'{STATE_FOLDER}/{key}.json', 'r') as f:
                all_states[key] = json.load(f)

def save_state(current_graph):
    global all_states
    with open(f'{STATE_FOLDER}/{current_graph}.json', 'w') as f:
        json.dump(all_states[key], f)


def validate_import(results):
    if not results:
        return
    result = results[0]
    if 'statistics' not in result:
        raise Exception('No statistics')
    if 'sourceFileName' not in result:
        raise Exception('No sourceFileName')
    return

def run_import_jobs(graph, claims, mentions, claims_mentions, sources, claims_sources):
    tigergraph_client = tigergraph[graph]
    # Upload claims
    results = tigergraph_client.upload_job(claims, 'load_claims')
    validate_import(results)
    # Upload mentions
    results = tigergraph_client.upload_job(mentions, 'load_mentions')
    validate_import(results)
    # Upload claims_mentions
    results = tigergraph_client.upload_job(claims_mentions, 'load_claims_mentions')
    validate_import(results)
    # Upload sources
    results = tigergraph_client.upload_job(sources, 'load_sources')
    validate_import(results)
    # Upload claims_sources
    results = tigergraph_client.upload_job(claims_sources, 'load_claims_sources')
    validate_import(results)
    print('=> Imported into ', graph, ' ', len(claims), 'claims, ', len(mentions), 'mentions, ', len(sources), 'sources')

def ping():
    while True:
        try:
            print('=> Ping', tigergraph[list(tigergraph.keys())[0]].ping())
        except Exception as e:
            print('Ping error', e)
        time.sleep(ping_interval)

if __name__ == '__main__':
    load_state()
    for key in tigergraph:
        tigergraph[key] = TigerGraph(key)
        tigergraph[key].connect()
    threading.Thread(target=extract_entities).start()
    threading.Thread(target=import_facts).start()
    threading.Thread(target=ping).start()
    print('Started importing')
