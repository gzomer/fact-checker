const BASE_URL = 'https://factchecker.futur.technology'

function doFactChecking(url, cb) {
    fetch(BASE_URL + "/fact_check?url=" + url)
        .then(response => response.json())
        .then(data => {
            cb(data)
        })
        .catch(error => {
            cb(null)
        })
}


chrome.action.onClicked.addListener(tab => {
    chrome.scripting.executeScript({
        target: { tabId: tab.id },
        files: [
            "./content.js"
        ]
    })
    .then(() => {
        doFactChecking(tab.url, function(data) {
            chrome.tabs.sendMessage(tab.id, {
                message: 'fact-check',
                data: data
            })
        })
    })
    .catch(err => console.log(err));
});