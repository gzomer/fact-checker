
function parse($) {
    let data = []
    try {
        $('.alignleft tr').each(function() {
            let claimStatus = $(this).find('td:nth-child(1)').text()
            // claim source e.g. Claim by Mary Miller (R):
            let span =  $(this).find('td:nth-child(2)').find('span')
            let claimSource = span.find('strong:nth-child(1)').text()
            let claimText = span.find('span:nth-child(2)').text()
            let claimUrl = null
            span.find('a').each(function(index, item){
                if ($(item).attr('href').includes('mediabiasfactcheck.com')) {
                    return
                }
                if (claimUrl != null) {
                    return
                }
                claimUrl = $(item).attr('href')
            })
            data.push({
                status: claimStatus,
                source: claimSource,
                text: claimText,
                url: claimUrl
            })
        })

        data = data.filter(item => item.url != null && item.text != null && item.url != '' && item.text != '' && item.status != null && item.status != '')
        // Map status
        data = data.map(item => {
            item.status = item.status.toLowerCase()
            if (item.status.includes('lie')) {
                item.status = 'false'
            }
            item.source = item.source.replace(':', '').trim()
            item.text = item.text.trim()
            return item
        })
        data = data.filter(item => item.url != null && item.text != null && item.url != '' && item.text != '' && item.status != null && item.status != '')
        data = data.filter(item => item.status == 'false' || item.status == 'true')
    } catch (e) {
        console.log(e)
    }

    data = data.map(item => {
        item.veracity = item.status
        item.claim = item.text
        delete item.status
        delete item.text
        return item
    })

    return data
}

module.exports = {
    parse
}