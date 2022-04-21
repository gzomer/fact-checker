# FactChecker

## Problem Statement

Misinformation is everywhere, in social media, websites, and even face-to-face. It’s hard to know what to believe, and even harder to figure out what’s true.

Misinformation has severe consequences. It can lead to health scares, like the anti-vaccination movement. It can cause political instability, like the 2016 U.S. Presidential Election. It can even lead to murder, like the case of the Pizzagate conspiracy theory.

Existing solutions have failed due a number of reasons:
- Lack of accurate, up-to-date data: Most fact-checking organizations rely on manually collected data, which is often out-of-date or incomplete.
- Lack of centralized knowledge base: There is no central repository of fact-checked content, which makes it difficult to track the spread of misinformation and to identify new instances of misinformation.
- Lack of platform coverage: Most fact-checking organizations only operate on one platform (e.g. Facebook), making it difficult to reach users on other platforms (e.g. WhatsApp).
- Lack of scale: Fact-checking organizations are often small, with limited resources. They can only fact-check a limited number of claims.
- Lack of language coverage: Most fact-checking organizations only operate in one language, making it difficult to reach a global audience.

Our solution for all these problems is a multi-platform, multi-lingual, real-time fact-checking system powered by machine learning and graph technology.

## Solution

- Large knowledge graphs of facts automatically harvested from the web
- Crawlers to automatically extract facts from the web
- iOS App to fact check information from Facebook, Twitter, Websites, and via voice
- Chrome extension to fact check websites
- Twitter bot to automatically monitor bad actors and fake tweets
- Fact spotter to extract relevant facts
- Semantic and reasoning-based fact checking

![](https://challengepost-s3-challengepost.netdna-ssl.com/photos/production/software_photos/001/911/921/datas/original.png)


# Architecture

![Architecture](https://challengepost-s3-challengepost.netdna-ssl.com/photos/production/software_photos/001/911/922/datas/gallery.jpg)

![Fact Checking](https://challengepost-s3-challengepost.netdna-ssl.com/photos/production/software_photos/001/911/923/datas/original.png)

![Twitter bad actors9](https://challengepost-s3-challengepost.netdna-ssl.com/photos/production/software_photos/001/911/924/datas/gallery.jpg)

### Graph size
![Wikidata graph](https://challengepost-s3-challengepost.netdna-ssl.com/photos/production/software_photos/001/911/981/datas/original.jpg)

# Installation

1. Creating graphs
2. Importing data
3. Facts crawler
4. Facts importer
5. Facts spotter
6. Twitter Bot Monitor
7. Twitter Bot Importer
8. Fact checking server
9. Chrome Extension
10. iOS App

## Creating graphs and importing data

```bash
cd fact-server
python -m venv env
source ./env/bin/activate
pip install -r requirements.txt
```

To create the FactChecking and NewsFacts graphs, run the following command:
```bash
python setup.py
```

To create the TwitterBadActors graph,run the following command:
```bash
python setup_bad_actors.py
```

Finally, use the following [Jupyter Notebook](https://colab.research.google.com/drive/1IZsHbkBlq6uUxh7DDupIVegCOg6VPyWL) to create the WikiData graph and download the dataset and upload the data.

## Facts crawler

We need to start the crawler in order to monitor the fact checking websites and media outlets.

Make sure you have MongoDB installed and running. MongoDB is used to store the webpage contents before they are processed and imported into TigerGraph database.

Then run the following:

```bash
cd fact-crawler
npm install
```

Then start the crawler by running
```bash
node app.js
```

The crawler will now fetch from multiple sources (including Snopes, MediaBias, BBC, NewYork Times, among others).

## Facts importer

The crawler fetches the facts into a temporary MongoDB database.

Now we need to run the importer to import the claims into the TigerGraph database.

```bash
cd fact-server
python -m venv env
source ./env/bin/activate
pip install -r requirements.txt
```

Then start Facts Importer
```bash
python start facts_importer.py
```

## Facts spotter

Fact Spotter is used to automatically extract claims from news articles.

### Machine learning model

To train the model use the following
[Jupyter Notebook](https://colab.research.google.com/drive/1omMiFLzTVGtioQ8lcifjW0joK0KIPeZG#scrollTo=t13DWBvYJJMF).

You can also the pre-trained model I have made available on [HuggingFace](https://huggingface.co/gzomer/claim-spotter-multilingual).

### Start spotter

First, install the packages:
```bash
cd fact-server
python -m venv env
source ./env/bin/activate
pip install -r requirements.txt
```

Then start Facts Spotter
```bash
python start spotter.py
```

## Twitter Bot Monitor

First, install the twitter bot packages:

```bash
cd fact-twitter-bot
npm install
```

Then start Twitter bot monitoring
```bash
node monitor.js
```

## Twitter Bot Importer

Twitter Bot importer imports the fetched accounts into TigerGraph.

First, install the twitter importer packages:
```bash
cd fact-twitter-bot
python -m venv env
source ./env/bin/activate
pip install -r requirements.txt
```

Then start Twitter Accounts importer
```bash
python importer.py
```

### Fact checking server

Fact server is responsible for doing fact checking using semantinc and reasoning-based approaches.

```bash
cd fact-server
python -m venv env
source ./env/bin/activate
pip install -r requirements.txt
```

Then start Facts Server
```bash
python start app.py
```

### Chrome Extension

Install the live version from [here](https://chrome.google.com/webstore/detail/factchecker/kmndaonnppdmhmbankbfhlfjodboilkn)

If you want to develop locally:

1. Goto Chrome Settings using three dots on the top right corner.
2. Now, Enable developer mode.
3. Click on Load Unpacked and select your Unzip folder. Note: You need to select the folder in which the manifest file exists.
4. The extension will be installed now.

### iOS App

Install the live version from [here](https://factchecker.futur.technology/ios)

To edit locally, open the project using XCode.


