import json
import os
import time

from os import listdir

from tigergraph import get_tigergraph

import_folder = "./retweets/"
interval_accounts = 5
tigergraph = None
graphname = 'TwitterBadActors'

def list_pending_accounts():
    accounts = []
    for file in listdir(import_folder):
        if file.endswith(".json"):
            accounts.append(file)
    return accounts

def get_accounts_to_monitor():
    results = tigergraph.list_accounts()
    if not results:
        return
    accounts = results[0]['(@@accounts)']
    accounts = [account for account in accounts if account['Account'].strip()]
    map_accounts = {account['Account']: account['ActorType'] for account in accounts}
    with open('./initial_bad_actors.txt', 'r') as f:
        for line in f:
            if line.strip() not in map_accounts:
                map_accounts[line.strip()] = 'bad_actor'
                accounts.append({'Account': line.strip(), 'ActorType': 'bad_actor'})

    # Save to file
    with open('./monitored_accounts.json', 'w') as f:
        json.dump(accounts, f, indent=4)

    return map_accounts

def escape_text(text):
    # Replace \n with \\n
    return text.replace('\n', ' ')

def import_account_relations(data, monitored_accounts):
    relations = []
    if 'statuses' not in data or not data['statuses']:
        return
    for tweet in data['statuses']:
        # If there is no retweet or there is quote continue
        if 'retweeted_status' not in tweet or 'quoted_status' in tweet:
            continue
        if tweet['user']['id'] == tweet['retweeted_status']['user']['id']:
            continue

        if tweet['user']['screen_name'] not in monitored_accounts:
            print(f'Skipping from {tweet["user"]["screen_name"]}')
            continue
        retweet_actor_type = 'unknown'
        if tweet['retweeted_status']['user']['screen_name'] in monitored_accounts:
            retweet_actor_type = monitored_accounts[tweet['retweeted_status']['user']['screen_name']]

        row = {}
        # Add user and retweeted user to row
        row['FromId'] = tweet['user']['id']
        row['FromName'] = tweet['user']['name']
        row['FromScreenName'] = tweet['user']['screen_name']
        row['FromLocation'] = tweet['user']['location']
        row['FromDescription'] = escape_text(tweet['user']['description'])
        row['FromFollowersCount'] = tweet['user']['followers_count']
        row['FromFriendsCount'] = tweet['user']['friends_count']
        row['FromListedCount'] = tweet['user']['listed_count']
        row['FromStatusesCount'] = tweet['user']['statuses_count']
        row['FromProfileImage'] = tweet['user']['profile_image_url']
        row['FromCreatedAt'] = tweet['user']['created_at']
        row['FromActorType'] = monitored_accounts[tweet['user']['screen_name']]
        row['FromOriginalActorType'] = 'bad_actor'
        row['SourceId'] = tweet['retweeted_status']['user']['id']
        row['SourceName'] = tweet['retweeted_status']['user']['name']
        row['SourceScreenName'] = tweet['retweeted_status']['user']['screen_name']
        row['SourceLocation'] = tweet['retweeted_status']['user']['location']
        row['SourceDescription'] = escape_text(tweet['retweeted_status']['user']['description'])
        row['SourceFollowersCount'] = tweet['retweeted_status']['user']['followers_count']
        row['SourceFriendsCount'] = tweet['retweeted_status']['user']['friends_count']
        row['SourceListedCount'] = tweet['retweeted_status']['user']['listed_count']
        row['SourceStatusesCount'] = tweet['retweeted_status']['user']['statuses_count']
        row['SourceProfileImage'] = tweet['retweeted_status']['user']['profile_image_url']
        row['SourceCreatedAt'] = tweet['retweeted_status']['user']['created_at']
        row['SourceActorType'] = retweet_actor_type
        row['SourceOriginalActorType'] = retweet_actor_type
        relations.append(row)

    account = data['statuses'][0]['user']['screen_name']

    if not relations:
        print('No relations to import for', account)
        return

    print('Start importing relations for', account, 'with', len(relations), 'relations')
    tigergraph.upload_job(relations, 'load_relations')
    print('Finished importing relations for', account)


def process_acounts_tweets():
    while True:
        print('Listing next accounts to import')
        monitored_accounts = get_accounts_to_monitor()
        for account in list_pending_accounts():
            print(f'Processing {account}')
            with open(import_folder + account) as f:
                data = json.load(f)
                import_account_relations(data, monitored_accounts)
                # Move file to processed folder (mkdir if not exists)
                if not os.path.exists(import_folder + '/processed'):
                    os.makedirs(import_folder + '/processed')
                filename = account.split('.')[0] + '.' + str(int(time.time())) + '.json'
                os.rename(import_folder + account, import_folder + 'processed/' + filename)
            time.sleep(interval_accounts)
        time.sleep(interval_accounts*2)

if __name__ == '__main__':
    tigergraph = get_tigergraph(graphname)
    process_acounts_tweets()
