import os
import re
import time
import pickle
import logging as log
import requests
from pprint import pformat
from base64 import b64encode, b64decode
from xmlParser import createAllegroProducts

log.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))
log = log.getLogger(__name__)

global tokenObj
global OAuthCodeEnc


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
    global tokenObj, OAuthCodeEnc

    clientID = '129bf27db850446a9104a88bbfa02c41'
    clientSecret = 'jU0lMTUOF6v29thseEVib1drsBNmngrHUhR5l0mAPsOpTNqLQBbZ9MlfUMsQ0pTB'
    OAuthCode = clientID + ':' + clientSecret
    OAuthCodeEnc = b64encode(OAuthCode.encode()).decode()
    OAuthUri = 'https://allegro.pl/auth/oauth/device'
    OAuthTokenUri = '''
            https://allegro.pl/auth/oauth/token?grant_type=urn%3Aietf%3Aparams%3Aoauth%3Agrant-type%3Adevice_code&'''
    contentType = 'application/x-www-form-urlencoded'

    try:
        tokenObj = readToken()
        return
    except IOError:
        log.debug('No saved token found!\r\n'
                  'Must get new one...')

    resp = _rest('POST', OAuthUri,
                 headers={
                     'Authorization': 'Basic ' + OAuthCodeEnc,
                     'Content-Type': contentType},
                 data='client_id=' + clientID)

    OAuthTokenUri += 'device_code=' + resp['device_code']

    print('CLICK HERE TO CONFIRM ACCESS GRANT >>> ' + resp['verification_uri_complete'] +
          ' <<< CLICK HERE TO CONFIRM ACCESS GRANT')

    resp = _rest('POST', OAuthTokenUri,
                 headers={'Authorization': 'Basic ' + OAuthCodeEnc})

    saveToken(resp)
    tokenObj = readToken()

    log.debug('\r\nCreated NEW tokenObj:')
    log.debug(pformat(tokenObj))
    log.debug('')


def refreshAccessToken():
    global tokenObj

    resource = 'https://allegro.pl/auth/oauth/token?grant_type=refresh_token&refresh_token={}' \
        .format(tokenObj['refresh_token'])

    resp = _rest('POST', resource,
                 headers={'Authorization': 'Basic ' + OAuthCodeEnc})
    saveToken(resp)
    tokenObj = readToken()


def getSellerID():
    """Decode sellerID from access token"""
    global tokenObj

    b64_string = tokenObj['access_token'] + "=" * (
            (4 - len(tokenObj['access_token']) % 4) % 4 + 1)  # adds proper padding to base64 string
    matchObj = re.search(b'\"user_name\":\"([0-9]+)\"', b64decode(b64_string))
    sellerID = matchObj.group(1).decode("UTF-8")
    log.debug(sellerID)

    return sellerID


def _rest(method, resource, bearer=False, headers=None, data=None):
    header = dict()

    if bearer is True:
        header = {
            'Authorization': 'Bearer ' + tokenObj['access_token'],
            'accept': 'application/vnd.allegro.public.v1+json',
            'content-type': 'application/vnd.allegro.public.v1+json'
        }

    if headers is not None:
        header.update(headers)

    for i in range(3):
        req = requests.Request(method, resource,
                               headers=header,
                               data=data).prepare()
        prettyLogRequest(req)

        s = requests.Session()

        resp = s.send(req)
        if resp.status_code == 200:
            break
        elif resp.status_code == 401 and bearer is True:
            refreshAccessToken()
            header.update({'Authorization': 'Bearer ' + tokenObj['access_token']})

        time.sleep(5)

    log.debug('Response:\n' +
              pformat(resp.json()))

    return resp.json()


def getDeliveryMethods():
    return _rest('GET', 'https://api.allegro.pl/sale/delivery-methods', bearer=True)


def getShippingRates():
    return _rest('GET', 'https://api.allegro.pl/sale/shipping-rates?seller.id=' + getSellerID(), bearer=True)


def getCategoryParams(categoryID):
    return _rest('GET', 'https://api.allegro.pl/sale/categories/{}/parameters'.format(categoryID), bearer=True)


def getOffers(sellerID, phrase, limit=5):
    return _rest('GET', 'https://api.allegro.pl/offers/listing?seller.id={}&phrase={}&limit={}'
                 .format(sellerID, phrase, limit), bearer=True)


def getMyOffers(name=None, status='ACTIVE', limit=5):
    res = 'https://api.allegro.pl/sale/offers?publication.status={}&limit={}'.format(status, limit)
    if name is not None:
        res += '&name=' + name

    return _rest('GET', res, bearer=True)


def postImages(allegroProduct):
    _rest('POST', 'https://api.allegro.pl/sale/images',
          data={
              'url': '{}'.format(img) for img in allegroProduct.getImages()
          })


def getOfferDetails(offerID):
    return _rest('GET', 'https://api.allegro.pl/sale/offers/{}'.format(offerID), bearer=True)


def main():
    deviceFlowOAuth()
    # getShippingRates()
    # getCategoryParams('257687')
    # products = createAllegroProducts('/home/daniel/Documents/1_praca/1_Freelance/1_handel/'
    #                                  '1_allegro/1_sklepy/LuckyStar/sklep.xml')
    # prod = products.pop()
    # postImages(prod)
    getOfferDetails('9068419944')


if __name__ == '__main__':
    main()
