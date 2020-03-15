import os
import re
import time
import pickle
import logging as log
import requests
from pprint import pformat
from base64 import b64encode, b64decode

log.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))
log = log.getLogger(__name__)

global tokenObj


def prettyLogRequest(req):
    """
    Logs REST request in pretty, readable format
    """
    log.debug('REST request:\n{}\n{}\r\n{}\r\n{}\r\n{}'.format(
        '-----------START-----------',
        req.method + ' ' + req.url,
        '\r\n'.join('{}: {}'.format(k, v) for k, v in req.headers.items()),
        req.body,
        '-----------END-----------',
    ))


def readToken():
    with open('allegro.token', 'rb') as tokenFile:
        tokenObj = pickle.load(tokenFile)

    return tokenObj


def saveToken(tokenObj):
    with open('allegro.token', 'wb') as tokenFile:
        pickle.dump(tokenObj, tokenFile)


def deviceFlowOAuth():
    global tokenObj
    clientID = '129bf27db850446a9104a88bbfa02c41'
    clientSecret = 'jU0lMTUOF6v29thseEVib1drsBNmngrHUhR5l0mAPsOpTNqLQBbZ9MlfUMsQ0pTB'
    OAuthCode = clientID + ':' + clientSecret
    OAuthCodeEnc = b64encode(OAuthCode.encode()).decode()
    OAuthUri = 'https://allegro.pl/auth/oauth/device'
    OAuthTokenUri = '''
            https://allegro.pl/auth/oauth/token?grant_type=urn%3Aietf%3Aparams%3Aoauth%3Agrant-type%3Adevice_code&'''
    contentType = 'application/x-www-form-urlencoded'

    try:
        return readToken()
    except IOError:
        log.debug('No saved token found!\r\n'
                  'Must get new one...')

    req = requests.Request('POST', OAuthUri, headers={
        'Authorization': 'Basic ' + OAuthCodeEnc,
        'Content-Type': contentType},
                           data='client_id=' + clientID).prepare()
    prettyLogRequest(req)

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
        prettyLogRequest(req)
        resp = s.send(req)
        log.debug('RESPONSE status: ' + str(resp.status_code) + '\r\n' +
                  'RESPONSE text: ')
        log.debug(pformat(resp.text))

        if resp.status_code == 200:
            break
    else:
        print('Authorization failed!')
        return

    tokenObj = resp.json()

    saveToken(tokenObj)
    tokenObj = readToken()

    log.debug('\r\nCreated NEW tokenObj:')
    log.debug(pformat(tokenObj))
    log.debug('')


def getDeliveryMethods():
    req = requests.Request('GET', 'https://api.allegro.pl/sale/delivery-methods',
                           headers={
                               'authorization': 'Bearer ' + tokenObj['access_token'],
                               'accept': 'application/vnd.allegro.public.v1+json',
                               'content-type': 'application/vnd.allegro.public.v1+json'},
                           # data={
                           #       "name": "Suszarka do włosów z dyfuzorem jonizacja",
                           #       "category": {
                           #           "id": "257150"
                           #       }
                           # }
                           ).prepare()
    prettyLogRequest(req)

    s = requests.Session()
    resp = s.send(req)
    log.debug('status: ' + str(resp.status_code) + '\r\n' +
              'text: ')
    log.debug(pformat(resp.text))


def getShippingRates():
    global tokenObj
    req = requests.Request('GET', 'https://api.allegro.pl/sale/shipping-rates?seller.id={Seller_IDD}',
                           headers={
                               'authorization': 'Bearer ' + tokenObj['access_token'],
                               'accept': 'application/vnd.allegro.public.v1+json',
                               'content-type': 'application/vnd.allegro.public.v1+json'},
                           ).prepare()
    prettyLogRequest(req)

    s = requests.Session()
    resp = s.send(req)
    log.debug('status: ' + str(resp.status_code) + '\r\n' +
              'text: ')
    log.debug(pformat(resp.text))


def getSellerID(tokenObj):
    """Decode sellerID from access token"""

    b64_string = tokenObj['access_token'] + "=" * ((4 - len(tokenObj) % 4) % 4)  # adds proper padding to base64 string
    matchObj = re.search(b'\"user_name\":\"([0-9]+)\"', b64decode(b64_string))
    sellerID = matchObj.group(1).decode("UTF-8")

    return sellerID


def main():
    global tokenObj

    tokenObj = deviceFlowOAuth()
    sellerID = getSellerID(tokenObj)
    log.debug(sellerID)


if __name__ == '__main__':
    main()
