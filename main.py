import os
import time
import pickle
import logging as log
import requests
from pprint import pformat
from base64 import b64encode

log.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))
log = log.getLogger(__name__)


def prettyLogPOST(req):
    """
    At this point it is completely built and ready
    to be fired; it is "prepared".

    However pay attention at the formatting used in
    this function because it is programmed to be pretty
    printed and may differ from the actual request.
    """
    log.debug('{}\n{}\r\n{}\r\n{}'.format(
        '-----------START-----------',
        req.method + ' ' + req.url,
        '\r\n'.join('{}: {}'.format(k, v) for k, v in req.headers.items()),
        req.body,
    ))


def readToken():
    with open('allegro.token', 'rb') as tokenFile:
        tokenObj = pickle.load(tokenFile)

    return tokenObj


def saveToken(tokenObj):
    with open('allegro.token', 'wb') as tokenFile:
        pickle.dump(tokenObj, tokenFile)


def deviceFlowOAuth():
    clientID = '129bf27db850446a9104a88bbfa02c41'
    clientSecret = 'jU0lMTUOF6v29thseEVib1drsBNmngrHUhR5l0mAPsOpTNqLQBbZ9MlfUMsQ0pTB'
    OAuthCode = clientID + ':' + clientSecret
    OAuthCodeEnc = b64encode(OAuthCode.encode()).decode()
    OAuthUri = 'https://allegro.pl/auth/oauth/device'
    OAuthTokenUri = '''
            https://allegro.pl/auth/oauth/token?grant_type=urn%3Aietf%3Aparams%3Aoauth%3Agrant-type%3Adevice_code&'''
    contentType = 'application/x-www-form-urlencoded'

    req = requests.Request('POST', OAuthUri, headers={
        'Authorization': 'Basic ' + OAuthCodeEnc,
        'Content-Type': contentType},
                           data='client_id=' + clientID).prepare()
    prettyLogPOST(req)

    s = requests.Session()
    resp = s.send(req)
    log.debug(resp.text)

    resp = resp.json()
    OAuthTokenUri += 'device_code=' + resp['device_code']

    print('CLICK HERE TO CONFIRM ACCESS GRANT >>> ' + resp['verification_uri_complete'] +
          ' <<< CLICK HERE TO CONFIRM ACCESS GRANT')
    for i in range(3):
        time.sleep(5)
        req = requests.Request('POST', OAuthTokenUri, headers={
            'Authorization': 'Basic ' + OAuthCodeEnc}).prepare()
        prettyLogPOST(req)
        resp = s.send(req)
        log.debug('status: ' + str(resp.status_code) + '\r\n' +
                  'text: ')
        log.debug(pformat(resp))

        if resp.status_code == 200:
            break
    else:
        print('Authorization failed!')
        return

    resp = resp.json()
    tokenObj = resp

    saveToken(tokenObj)
    tokenObj = readToken()

    log.debug('\r\ntokenObj:')
    log.debug(pformat(tokenObj))
    log.debug('')

    return tokenObj


def main():
    tokenObj = readToken()

    log.debug('\r\ntokenObj:')
    log.debug(pformat(tokenObj))
    log.debug('')


if __name__ == '__main__':
    main()
