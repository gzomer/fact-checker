const { downloadSources } = require('./sources');
const { fetchNext } = require('./factExtractor');
const cron = require('node-cron');

const ITEMS_PARALLEL = 2;
const INTERVAL = 5000;

(function(){
    // Run interval every 5 seconds
    setInterval(function() {
        // Find next 5 links that are not processed yet
        fetchNext(ITEMS_PARALLEL)
    }, INTERVAL);

    // Cron job to download sources every 1 hours and also at startup
    downloadSources();
    cron.schedule('0 0 */1 * * *', function() {
        downloadSources();
    });
})();
