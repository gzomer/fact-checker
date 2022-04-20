const async = require('async');
const fs = require('fs');
const fetch = require('node-fetch');

const keys = JSON.parse(fs.readFileSync('./keys.json'));

const credentials = `${keys.consumer_key}:${keys.consumer_secret}`;
const credentialsBase64Encoded = Buffer.from(credentials).toString('base64');

const CHECK_URL = 'https://factchecker.futur.technology/fact_check'
const CHECK_THRESHOLD = 0.9
const CHECKING_PARALLEL = 1
const CHECKING_PARALLEL_ITEMS = 10
const CHECKING_INTERVAL = 5000
const WAIT_INTERVAL = 60000
const WAIT_BETWEEN_CHECKS = 500
const LAST_CHECKED_INTERVAL = 3*60*60*1000;
const WAIT_BETWEEN_ACCOUNTS = 15000
const MONITORED_ACCOUNTS_FILE = './monitored_accounts.json'
const STATE_FOLDER = './state/'
const TWEETS_STATE_FILE = './state/tweets_fact_checking.json'

let messages = [
    'I think you should check this article',
    'I believe you would benefit from reading this article',
    'This article may be of interest to you',
    'I suggest you read this article',
    'You might find this article helpful',
    'Have you seen this article?',
    'You should take a look at this article',
]

const lastCheckedAccounts = {
    'tweets' : {},
    'retweets' : {}
};
let tweetsFactChecking = {}

// Convert code above to nodefetch
function getToken() {
    // Credentials from keys.json
    const credentialsBase64Encoded = Buffer.from(`${keys.consumer_key}:${keys.consumer_secret}`).toString('base64');
    return fetch('https://api.twitter.com/oauth2/token', {
        method: 'POST',
        headers: {
            'Authorization': `Basic ${credentialsBase64Encoded}`,
            'Content-Type':'application/x-www-form-urlencoded;charset=UTF-8'
        },
        body: 'grant_type=client_credentials'
    })
    .then(res => res.json())
    .then(json => console.log(json));
}

const search = (query) => {
    const url = `https://api.twitter.com/1.1/search/tweets.json?q=${query}&count=100&tweet_mode=extended`;
    const auth = Buffer.from(`${keys.consumer_key}:${keys.consumer_secret}`).toString('base64');
    const options = {
        headers: {
            'Authorization': 'Bearer ' + TOKEN
        }
    }
    return fetch(url, options)
        .then(res => res.json())
        .then(json => json)
        .catch(err => console.log(err));
}

function saveIndividualTweets(data, type) {
    const tweets = data.statuses;
    for (tweet of tweets) {
        let selectedTweet = null
        if (type == 'retweets') {
            if (typeof tweet.retweeted_status === 'undefined') {
                continue;
            }
            if (typeof tweet.quoted_status !== 'undefined') {
                continue;
            }
            selectedTweet = tweet.retweeted_status;
        } else if (type == 'tweets') {
            if (typeof tweet.retweeted_status !== 'undefined') {
                continue;
            }
            if (typeof tweet.quoted_status !== 'undefined') {
                continue;
            }
            selectedTweet = tweet;
        }

        const fileTweet = `./${STATE_FOLDER}/tweets/${selectedTweet.id}.json`
        if (fs.existsSync(fileTweet)) {
            continue;
        }
        fs.writeFileSync(fileTweet, JSON.stringify(selectedTweet, null, 2));
        if (typeof tweetsFactChecking[selectedTweet.id] === 'undefined') {
            tweetsFactChecking[selectedTweet.id] = {
                id: selectedTweet.id,
                text: selectedTweet.full_text,
                user: selectedTweet.user.screen_name,
                fact_checking: 'pending'
            }
        }
    }
    fs.writeFileSync(TWEETS_STATE_FILE, JSON.stringify(tweetsFactChecking, null, 2));
}

function saveTweets(account, data, type) {
    //Mkdir if not exists
    let outputFolder = `./${type}`
    if (!fs.existsSync(outputFolder)) {
        fs.mkdirSync(outputFolder);
    }
    fs.writeFileSync(`${outputFolder}/${account}.json`, JSON.stringify(data, null, 2));
    saveIndividualTweets(data, type);
}

function saveLastChecked(account) {
    lastCheckedAccounts[account] = new Date().getTime();
}

function searchAndSave(account, type) {
    if (lastCheckedAccounts && lastCheckedAccounts[type] && lastCheckedAccounts[type][account] && new Date().getTime() - lastCheckedAccounts[type][account] < LAST_CHECKED_INTERVAL) {
        console.log(`${account} already checked recently. Skipping...`);
        return;
    }
    if (fs.existsSync(`./${type}/${account}.json`)) {
        console.log(`${account} data already fetched`);
        return;
    }
    let query = ''
    if (type === 'tweets') {
        query = `from:${account} -filter:retweets`
    } else if (type === 'retweets') {
        query = `from:${account} filter:retweets`
    }
    return search(query)
    .then(tweets => {
        saveTweets(account, tweets, type);
        saveLastChecked(account);
    })
    .catch(err => console.log('=> Error monitoring account:', account, err));
}

function searchAndSaveRetweets(account) {
    return searchAndSave(account, 'retweets');
}

function searchAndSaveTweets(account) {
    return searchAndSave(account, 'tweets');
}

function getAccountsToMonitor() {
    // Load monitored accounts.json
    if (!fs.existsSync(MONITORED_ACCOUNTS_FILE)) {
        return []
    }
    const accounts = JSON.parse(fs.readFileSync(MONITORED_ACCOUNTS_FILE));
    return accounts.map(item=>item.Account)
}

function timeout(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

async function monitor() {
    TOKEN = await getToken()

    while (true) {
        const accountsToMonitor = getAccountsToMonitor();
        console.log('=> Found', accountsToMonitor.length, 'accounts to monitor');
        for (account of accountsToMonitor) {
            console.log(`Monitoring ${account}`);
            await searchAndSaveRetweets(account);
            await searchAndSaveTweets(account);
            await timeout(WAIT_BETWEEN_ACCOUNTS)
        }
        await timeout(WAIT_INTERVAL)
    }
}

function loadTweetsState() {
    if (!fs.existsSync(TWEETS_STATE_FILE)) {
        return {}
    }
    return JSON.parse(fs.readFileSync(TWEETS_STATE_FILE));
}

async function factCheckTweet(tweet) {
    // Fact check tweet and save result in state
    const url = `${CHECK_URL}?text=` + encodeURIComponent(tweet.text) + `&threshold=${CHECK_THRESHOLD}`;
    console.log('=> Checking tweet', tweet.id)
    return fetch(url)
        .then(res => res.json())
        .then(json => {
            console.log('=> Tweet checked', tweet.id, json);
            if (json && json.type == 'found') {
                tweetsFactChecking[tweet.id].fact_checking = json.check
            } else {
                tweetsFactChecking[tweet.id].fact_checking = 'not_found'
            }
            return timeout(WAIT_BETWEEN_CHECKS).then(() => {
                return json
            })
        })
        .catch(err => console.log('=> Error fact checking tweet:', tweet.id, err));
}

function factCheckingTweets() {
    const tweetsPending = Object.values(tweetsFactChecking).filter(tweet => tweet.fact_checking === 'pending');
    console.log('=> Found', tweetsPending.length, 'tweets pending');
    async.mapLimit(tweetsPending.slice(CHECKING_PARALLEL_ITEMS), CHECKING_PARALLEL, factCheckTweet, (err, results) => {
        if (err) {
            console.log(err);
        }
        fs.writeFileSync(TWEETS_STATE_FILE, JSON.stringify(tweetsFactChecking, null, 2));
        setTimeout(factCheckingTweets, CHECKING_INTERVAL);
    })
}

function sendTweet(status, replyId) {
    return new Promise((resolve, reject) => {
        T.post('statuses/update', {
            status: status,
            in_reply_to_status_id: replyId
            }, function(err, data, response) {
                if (err) {
                    console.log('=> ERROR', err);
                    reject(err);
                } else {
                    console.log('Tweeted: ' + status);
                    resolve(data);
                }
            }
        )
    })
}


async function replyFakePost(t) {
    let message = messages[Math.floor(Math.random() * messages.length)];
    // Start with  screen_name and include url from query urls
    let query = t.query;
    let urls = queries.find(q => q.query == query).urls;
    let url = urls[Math.floor(Math.random() * urls.length)];
    let status = `@${t.tweet.screen_name} ${message} ${url}`;

    try {
        await sendTweet(status, t.tweet.id);
        return true
    } catch(err) {
        return false
    }
}

function sendFactCheckingReplies() {
    setInterval(() => {
        let relevantTweets = Object.values(tweetsFactChecking).filter(tweet => tweet.fact_checking !== 'not_found' && tweet.fact_checking !== 'pending');
        console.log('=> Found', relevantTweets.length, 'tweets to reply');
        // Filter out only false tweets
        relevantTweets = relevantTweets.filter(tweet => tweet.fact_checking === false);
        console.log('=> Found', relevantTweets.length, 'false tweets');
        relevantTweets.forEach(tweet => {
            replyFakePost(tweet)
        })
    }, 10000);
}
function main() {
    tweetsFactChecking = loadTweetsState();
    factCheckingTweets();
    monitor();
    sendFactCheckingReplies()
}

main()