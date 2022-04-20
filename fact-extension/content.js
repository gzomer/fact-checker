function showView(data) {
    if (data == null) {
        data = {
            "type": "not_found",
            "message": "No fact-checking found for this page."
        }
    }
    let color = 'grey';
    if (data.type === 'found') {
        if (data.check) {
            color = '#0c790c'
            result = 'TRUE'
        } else {
            color = '#a50000'
            result = 'FALSE'
        }
    }
    else {
        result = 'NOT FOUND'
    }
    // Remove if exists
    let currentElement = document.getElementById('factchecker-message')
    if (currentElement) {
        currentElement.remove()
    }

    document.body.innerHTML += `
        <style type="text/css">
            @namespace svg "http://www.w3.org/2000/svg";
            .factchecker-message {
                all: initial !important;
                width: 300px!important;
                background-color: white!important;
            }
            .factchecker-message a,
            .factchecker-message h1,
            .factchecker-message p,
            .factchecker-message div {
                all: initial !important;
                font-family: sans-serif !important;
                display: block!important;
            }
            .factchecker-message a {
                text-decoration: underline !important;
                cursor: pointer !important;
                width: 100% !important;
                text-align: center !important;
                font-size: 14px!important;
            }
            .factchecker-message h1 {
                font-size: 20px!important;
                margin-bottom: 10px!important;
            }
            .factchecker-message p {
                font-size: 16px!important;
                margin-bottom: 5px!important;
            }
            .factchecker-message svg {
                position: absolute!important ;
                top: 5px; right: 5px!important;
                cursor: pointer!important;
            }
            .factchecker-message {
                position: fixed!important;
                top: 10px!important;
                right: 10px!important;
                border-radius: 5px!important;
                padding: 10px!important;
                box-shadow: 0 4px 8px 0 rgba(0, 0, 0, 0.2), 0 6px 20px 0 rgba(0, 0, 0, 0.19)!important;
                z-index: 100000!important;
                cursor: pointer!important;
                padding-right: 30px!important;
                font-family: sans-serif!important;
            }
            .factchecker-message .factchecker-result {
                background-color: ${color}!important;
                color: ${data.type === 'not_found' ? 'black' : 'white'}!important;
                width: 100%!important;
                height: 40px!important;
                text-align: center!important;
                line-height: 40px!important;
                margin-bottom: 10px!important;
            }
        </style>
        <div class="factchecker-message" id="factchecker-message">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-x-circle" id="close-icon"><circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line></svg>
            ${data.type == 'found' ? `<h1>${data.title}</h1>` : ''}
            <p>${data.message}</p>
            <div class="factchecker-result">
                ${result}
            </div>
            ${data.type == 'found' ? `<a href="${data.source }" target="_blank">View Source</a>` : ''}
        </div>
    `

    document.getElementById('close-icon').addEventListener('click', function () {
        document.getElementById('factchecker-message').remove()
    })
}

// Receive message from service worker
chrome.runtime.onMessage.addListener(function (request, sender, sendResponse) {
    if (request.message === 'fact-check') {
        showView(request.data)
    }
    sendResponse({
        message: 'done'
    })
})
