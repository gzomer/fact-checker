const fs = require('fs');
const yaml = require('js-yaml');
const fetch = require('node-fetch');
const async = require('async');
const xml2js = require('xml2js');
const sourcesFile = './sources.yml';
const models = require('./models');
const mongoose = require('mongoose');

mongoose.connect('mongodb://localhost/factchecker', { useUnifiedTopology: true, useNewUrlParser: true });

const lastModifiedYear = 2020;
const DEFAULT_GRAPH = 'FactChecking'

function loadSources(filePath) {
    var fileContent = fs.readFileSync(filePath, 'utf8');
    return yaml.load(fileContent);
}

async function parseAndSaveSitemap(body, url, source) {
    console.log('Parsing sitemap url')
    let urls = await parseSitemap(body, url, source);
    try {
        await saveURLs(urls, source);
    } catch (err) {
        if (err.message.indexOf('duplicate key error') > -1) {
            console.log('Duplicate key error, skipping');
        } else {
            throw err;
        }
    }
}

async function parseAndSaveRSS(body, url, source) {
    console.log('Parsing rss url')
    let urls = await parseRSS(body, url, source);
    try {
        await saveURLs(urls, source);
    } catch (err) {
        if (err.message.indexOf('duplicate key error') > -1) {
            console.log('Duplicate key error, skipping');
        } else {
            throw err;
        }
    }
}

function processSitemap(url, source) {
    // Download sitemap and save each url to db (mongodb)
    console.log('Site map: ' + url)
    return fetch(url)
        .then(res => res.text())
        .then(body => {
            return parseAndSaveSitemap(body, url, source);
        })
        .catch(err => {
            console.log(err);
        })
}

function processRSS(url, source) {
    console.log('RSS: ' + url)
    return fetch(url)
        .then(res => res.text())
        .then(body => {
            return parseAndSaveRSS(body, url, source);
        })
        .catch(err => {
            console.log(err);
        })
}

function parseSitemap(body, url, source) {
    // Parse sitemap and save each url to db (mongodb)
    console.log('Parsing sitemap')
    return new Promise((resolve, reject) => {
        xml2js.parseString(body, function (err, result) {
            if (err) {
                console.log('Error parsing sitemap: ' + err);
                reject(err);
                return
            } else {
                console.log('Parsed sitemap')
                var urls = result.urlset.url.map(function(item) {
                    return item.loc[0]
                });
                resolve(urls);
            }
        })
    })
}

function parseRSS(body, url, source) {
    // Parse rss and save each url to db (mongodb)
    console.log('Parsing RSS')
    return new Promise((resolve, reject) => {
        xml2js.parseString(body, function (err, result) {
            if (err) {
                console.log('Error parsing rss: ' + err);
                reject(err);
                return
            } else {
                console.log('Parsed rss')
                var urls = result.rss.channel[0].item.map(function(item) {
                    return item.link[0].split('?')[0].split('#')[0]
                });
                resolve(urls);
            }
        })
    })
}

function saveURLs(urls, source) {
    let graph = DEFAULT_GRAPH;
    if (source.type == 'rss') {
        graph = 'NewsFacts';
    } else {
        graph = 'FactChecking';
    }

    let items = urls.map(function(url) {
        return {
            url: url,
            source: source.name.toLowerCase(),
            graph: graph
        }
    });
    console.log('Saving ' + items.length + ' urls');
    return new Promise((resolve, reject) => {
        models.Link.insertMany(items, {ordered: false}, function(err, docs) {
            if (err) {
                reject(err);
                return
            } else {
                console.log('Saved ' + docs.length + ' urls');
                resolve();
            }
        })
    })
}

function downloadSources(config) {
    /*
        For each source check if type is sitemap_index or sitemap
        If sitemap_index, filter out sitemaps loc by pattern and lastmod and process each sitemap
        If sitemap, process sitemap
    */
    var sources = loadSources(sourcesFile);
    if ( typeof config !== 'undefined' && config.sources ) {
        sources = sources.slice(0, config.sources);
    }
    async.mapLimit(sources, 1, async function(source) {
        if (source.type === 'sitemap_index') {
            return processSitemapIndex(source, config);
        } else if (source.type === 'sitemap') {
            return processSitemap(source.url, source);
        } else if (source.type === 'rss') {
            return processRSS(source.url, source);
        }
    }, function(err, results) {
        if (err) {
            console.log('Error downloading sources: ' + err);
        } else {
            console.log('Downloaded sources');
        }
    })
}

function filterSitemaps(sitemaps, source) {
    return sitemaps.filter(function(sitemap) {
        var lastmod = sitemap.lastmod[0];

        var lastmodYear = lastmod.substring(0, 4);
        if (lastmodYear >= lastModifiedYear && sitemap.loc[0].includes(source.pattern)) {
            return true
        }
        return false
    });
}

function getRecentSitemaps(body, source, config) {
    console.log('Parsing sitemap index')
    return new Promise((resolve, reject) => {
        xml2js.parseString(body, function (err, result) {
            if (err) {
                console.log('Error parsing sitemap index: ' + err);
                reject(err);
                return
            } else {
                console.log('Parsed sitemap index')
                var sitemaps = filterSitemaps(result.sitemapindex.sitemap, source);
                if ( typeof config !== 'undefined' && config.sitemaps ) {
                    sitemaps = sitemaps.slice(0, config.sitemaps);
                }
                async.mapLimit(sitemaps, 1, async function(sitemap, callback) {
                    return processSitemap(sitemap.loc[0], source);
                }, function(err, results) {
                    console.log('Finished index')
                    resolve();
                })
            }
        });
    })
}

function processSitemapIndex(source, config) {
    // Download sitemap index and filter out sitemaps loc by pattern and lastmod date and process each sitemap
    console.log('Site map index: ' + source.url)
    return fetch(source.url)
        .then(res => res.text())
        .then(body => {
            return getRecentSitemaps(body, source, config);
        })
        .catch(err => {
            console.log('Error fetching sitemap index: ' + err);
        })
}

module.exports = {
    downloadSources,
}