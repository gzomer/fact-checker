const models = require('./models');
const async = require('async');
const fetch = require('node-fetch');
const yaml = require('js-yaml');
const fs = require('fs');
const cheerio = require('cheerio');
const moment = require('moment');
const HeaderGenerator = require('header-generator');

const headerGenerator = new HeaderGenerator({
    browsers: [
        {name: "firefox", minVersion: 80},
        {name: "chrome", minVersion: 87},
    ],
    devices: [
        "desktop"
    ],
    operatingSystems: [
        "windows",
        "macos",
        "linux"
    ]
});

const factExtractor = yaml.load(fs.readFileSync('./facts_extractor.yml', 'utf8'));

function downloadPage(url) {
    const headers = headerGenerator.getHeaders();
    return fetch(url, { headers })
        .then(res => res.text())
        .then(body => {
            return cheerio.load(body);
        })
        .catch(err => {
            console.log(err);
        })
}

function extractInfo($, extractor) {
    // For each key in extractor, extract the value from the page
    // and save it to the data object
    const data = {};

    for (const key in extractor.data) {
        const value = extractor.data[key];
        if (typeof value === 'string') {
            data[key] = $(value).text().trim();
        } else if (typeof value === 'object') {
            let selected = $(value.selector);
            if (value.extract == 'text') {
                data[key] = $(value.selector).text().trim();
            } else if (value.extract == 'html') {
                data[key] = $(value.selector).html().trim();
            } else if (typeof value.extract.attr !== 'undefined') {
                data[key] = $(value.selector).attr(value.extract.attr);
            }
            if (typeof value.parser !== 'undefined') {
                let parser = value.parser;
                if (parser.type === 'date') {
                    try {
                        let date = moment(data[key]);
                        data[key] = date.format(parser.format);
                    } catch (err) {
                        console.log(err);
                    }
                } else if (parser.type === 'number') {
                    data[key] = parseFloat(data[key]);
                }
            }
        }
    }
    return data;
}

async function processItem(item) {
    try {

        const $ = await downloadPage(item.url);

        const extractor = factExtractor[item.source];
        if (typeof extractor['parser'] !== 'undefined') {

            let module = require('./parsers/' + item.source + '.js');
            let data = module.parse($);
            for (row of data) {
                const fact = new models.Fact({
                    url: row.url,
                    data: row,
                    source: item.source,
                    graph: item.graph,
                });
                await fact.save();
            }
        } else {
            const extractedInfo = extractInfo($, factExtractor[item.source]);
            if (Object.keys(extractedInfo).length > 0) {
                // Create new fact using url and extracted info (data)
                const fact = new models.Fact({
                    url: item.url,
                    data: extractedInfo,
                    source: item.source,
                    graph: item.graph,
                });
                await fact.save();
            }
        }
        item.processed = true;
    } catch (e) {
        item.error = true;
    }
    // Mark link as processed
    await item.save();
}


function fetchNext(itemsParallel) {
    // Find next 5 links that are not processed yet
    models.Link.find({ processed: false, error: false, graph: 'FactChecking'}).limit(itemsParallel).exec(function(err, links) {
        if (err) {
            console.log(err);
            return;
        }
        console.log('To process', links.length, 'links');
        async.mapLimit(links, itemsParallel, processItem, function(err, results) {
            if (err) {
                console.log(err);
                return;
            }
            console.log('Finished processing links');
        })
    })
}

module.exports = {
    fetchNext,
}