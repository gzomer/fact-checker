import random
from flask import Flask, jsonify, request, redirect
from factchecker import fact_check, fact_check_by_url
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route('/')
def index():
    return ""

@app.route('/privacy')
def privacy():
    # Return file named privacy.html
    return app.send_static_file('privacy.html')

@app.route('/ios')
def link_ios():
    return redirect('https://apps.apple.com/us/app/gustavozomer/id1618583438')

@app.route('/extension')
def link_ext():
    return redirect('https://chrome.google.com/webstore/detail/factchecker/kmndaonnppdmhmbankbfhlfjodboilkn')

@app.route('/fact_check', methods=['GET'])
def api_fact_check():
    url = request.args.get('url', None)
    text = request.args.get('text', None)

    if url:
        fact_checking, info = fact_check_by_url(url)
    elif text:
        fact_checking, info = fact_check(text)

    if not fact_checking:
        return jsonify({'info': info, 'type': 'not_found', 'message': 'Nothing to show'})
    else:
        title = ''
        if fact_checking['truth']:
            title = 'True statement'
        else:
            title = 'Attention: False claim'

        return jsonify({
            'type': 'found',
            'info': info,
            'message': fact_checking['text'],
            'title': title,
            'check': fact_checking['truth'],
            'source': fact_checking.get('source', 'https://factchecker.futur.technology'),
        })

if __name__ == '__main__':
    app.run(debug=True, port=5002)
