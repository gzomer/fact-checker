const fs = require('fs');
const express = require('express');
const oauth = require('oauth');
const app = express();
const session = require('express-session');
const Twit = require('twit')

app.use(session({
    secret: 'keyboard cat',
    resave: false,
    saveUninitialized: true,
    cookie: { secure: false }
}));

const keys = require('./keys.json');

const oa = new oauth.OAuth(
    'https://api.twitter.com/oauth/request_token',
    'https://api.twitter.com/oauth/access_token',
    keys.consumer_key,
    keys.consumer_secret,
    '1.0A',
    'http://localhost:3000/auth/twitter/callback',
    'HMAC-SHA1'
);

app.get('/auth/twitter', (req, res) => {
    oa.getOAuthRequestToken((error, oauth_token, oauth_token_secret, results) => {
        if (error) {
            console.log(error);
            res.send('yeah no. didn\'t work.');
        } else {
            req.session.oauth = {};
            req.session.oauth.token = oauth_token;
            console.log('oauth.token: ' + req.session.oauth.token);
            req.session.oauth.token_secret = oauth_token_secret;
            console.log('oauth.token_secret: ' + req.session.oauth.token_secret);
            res.redirect('https://twitter.com/oauth/authenticate?oauth_token=' + oauth_token)
        }
    });
});

app.get('/auth/twitter/callback', (req, res, next) => {
    if (req.session.oauth) {
        req.session.oauth.verifier = req.query.oauth_verifier;
        const oauth = req.session.oauth;

        oa.getOAuthAccessToken(oauth.token, oauth.token_secret, oauth.verifier,
            (error, oauth_access_token, oauth_access_token_secret, results) => {
                if (error) {
                    console.log(error);
                    res.send("yeah something broke.");
                } else {
                    req.session.oauth.access_token = oauth_access_token;
                    req.session.oauth.access_token_secret = oauth_access_token_secret;
                    const userTokens = {
                        access_token: oauth_access_token,
                        access_token_secret: oauth_access_token_secret
                    }
                    fs.writeFileSync('userTokens.json', JSON.stringify(userTokens, null, 2));
                    res.send("worked. nice one.");
                }
            }
        );
    } else {
        next(new Error("you're not supposed to be here."))
    }
});

app.listen(3000, () => {
    console.log('Server running on port 3000');
});
