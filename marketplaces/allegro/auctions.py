import os
import re
import uuid
import time
import pickle
import requests
import logging as log
from pprint import pformat
from base64 import b64encode, b64decode
import marketplaces.allegro.fileReader as Fr

MAX_TRIES = 1
ALLEGRO_TOKEN_FILE = 'allegro.token'
ALLEGRO_OFFERS_FILE = 'allegro.offers'
fmt = "[%(levelname)s:%(filename)s:%(lineno)s: %(funcName)s()] %(message)s"
log.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"), format=fmt)
log = log.getLogger(__name__)


class Auction:
    nextFreeNum = 1
    def __init__(self, integrator):
        self.template = {
            'name': None,
            'location': {'city': 'Łódź',
                         'countryCode': 'PL',
                         'postCode': '90-619',
                         'province': 'LODZKIE'},
            'payments': {'invoice': 'VAT'},
            'afterSalesServices': {
                'impliedWarranty': {'id': '95b451bf-7fd6-4d46-9bc1-ac6516eeb065'},
                'returnPolicy': {'id': 'f7b5005b-4b46-45d7-bab8-e17208729f2c'},
                'warranty': {'id': '593b3ed0-655c-40e6-acbc-7782351cca75'}},
            'delivery': {
                'handlingTime': 'PT24H',
                'shippingRates': {'id': 'cde2d24a-ab38-461d-96da-ade36d99e7cf'}},
            'stock': {'available': '2', 'unit': 'UNIT'},
            'category': {'id': '257698'},
            'sellingMode': {'format': 'BUY_NOW',
                            'price': {'amount': '609', 'currency': 'PLN'},
                            }
        }

        self.offer = None
        self.imgLinks = None
        self.restMod = RestAPI()
        self.integrator = integrator
        self.num = Auction.nextFreeNum
        self.incrementNextFreeNum()

        self.setEAN(integrator.getEAN())
        self.setCategory(integrator.getCategory())
        self.setPrice(integrator.getPrice())
        self.setTitle(integrator.getTitle())
        self.setImgLinks(integrator.getImages())
        self.setDescription(integrator.getDesc(self.imgLinks))
        self.setStockCount(integrator.getStockCount())
        self.setParams(integrator.getParams(self.getCategoryParams()))

        log.debug('\n\nCreated template:\n\n'
                  '{}'.format(pformat(self.template)))

    @staticmethod
    def setNextFreeNum(num):
        Auction.nextFreeNum = num
    def incrementNextFreeNum(self):
            Auction.nextFreeNum += 1

    def setTitle(self, name):
        self.template['name'] = name

    def setEAN(self, ean):
        self.template['ean'] = ean

    def setImgLinks(self, images):
        allegroLinks = RestAPI.postImages(images)
        self.imgLinks = [{'url': link} for link in allegroLinks]
        self.template['images'] = self.imgLinks

    def setCategory(self, category):
        self.template['category'] = category

    def setDescription(self, desc):
        self.template['description'] = desc

    def setParams(self, params):
        self.template['parameters'] = params

    def setStockCount(self, count):
        self.template['stock'] = count

    def setPrice(self, price):
        self.template['sellingMode']['price'] = price

    def push(self):
        self.offer = self.restMod.pushOffer(self.template)

    def saveOfferToFile(self):
        Fr.saveObjToFile(self.offer, ALLEGRO_OFFERS_FILE + '.' + str(self.num))


    def getTemplate(self):
        return self.template

    def getCategoryParams(self):
        return self.restMod.getCategoryParams(self.integrator.getCategory()['id'])


class RestAPI:
    def __init__(self):
        pass

    tokenObj = None
    OAuthCodeEnc = None

    @staticmethod
    def prettyLogRequest(req):
        """
        Logs REST request in pretty, readable format
        """
        log.debug('\nREST request:\n{}\n{}\r\n{}\r\n{}\r\n{}'.format(
            '-----------START-----------',
            req.method + ' ' + req.url,
            '\r\n'.join('{}: {}'.format(k, v) for k, v in req.headers.items()),
            req.body,
            '-----------END-----------',
        ))

    @staticmethod
    def readToken():
        return Fr.readObjFromFile(ALLEGRO_TOKEN_FILE)

    @staticmethod
    def saveToken(tokenObj):
        Fr.saveObjToFile(tokenObj, ALLEGRO_TOKEN_FILE)

    @staticmethod
    def deviceFlowOAuth():
        clientID = '129bf27db850446a9104a88bbfa02c41'
        clientSecret = 'jU0lMTUOF6v29thseEVib1drsBNmngrHUhR5l0mAPsOpTNqLQBbZ9MlfUMsQ0pTB'
        OAuthCode = clientID + ':' + clientSecret
        RestAPI.OAuthCodeEnc = b64encode(OAuthCode.encode()).decode()
        OAuthUri = 'https://allegro.pl/auth/oauth/device'
        OAuthTokenUri = '''
                https://allegro.pl/auth/oauth/token?grant_type=urn%3Aietf%3Aparams%3Aoauth%3Agrant-type%3Adevice_code&'''
        contentType = 'application/x-www-form-urlencoded'

        try:
            RestAPI.tokenObj = RestAPI.readToken()
            return
        except IOError:
            log.debug('No saved token found!\r\n'
                      'Must get new one...')

        resp = RestAPI._rest('POST', OAuthUri,
                             headers={
                                 'Authorization': 'Basic ' + RestAPI.OAuthCodeEnc,
                                 'Content-Type': contentType},
                             data='client_id=' + clientID)

        OAuthTokenUri += 'device_code=' + resp['device_code']

        print('CLICK HERE TO CONFIRM ACCESS GRANT >>>>>>>>>>>>>>>>>>>> ' + resp['verification_uri_complete'] +
              ' <<<<<<<<<<<<<<<<<<<< CLICK HERE TO CONFIRM ACCESS GRANT')

        resp = RestAPI._rest('POST', OAuthTokenUri,
                             headers={'Authorization': 'Basic ' + RestAPI.OAuthCodeEnc})

        RestAPI.saveToken(resp)
        RestAPI.tokenObj = RestAPI.readToken()

        log.debug('\r\nCreated NEW tokenObj:')
        log.debug(pformat(RestAPI.tokenObj))
        log.debug('')

    @staticmethod
    def refreshAccessToken():
        resource = 'https://allegro.pl/auth/oauth/token?grant_type=refresh_token&refresh_token={}' \
            .format(RestAPI.tokenObj['refresh_token'])

        resp = RestAPI._rest('POST', resource,
                             headers={'Authorization': 'Basic ' + RestAPI.OAuthCodeEnc})
        RestAPI.saveToken(resp)
        RestAPI.tokenObj = RestAPI.readToken()

    @staticmethod
    def _getSellerID():
        """Decode sellerID from access token"""

        b64_string = RestAPI.tokenObj['access_token'] + "=" * (
                (4 - len(RestAPI.tokenObj['access_token']) % 4) % 4 + 1)  # adds proper padding to base64 string
        matchObj = re.search(b'\"user_name\":\"([0-9]+)\"', b64decode(b64_string), re.IGNORECASE)
        sellerID = matchObj.group(1).decode("UTF-8")
        log.debug(sellerID)

        return sellerID

    @staticmethod
    def _rest(method, resource, bearer=False, headers=None, data=None, json=None):
        header = dict()

        if bearer is True:
            header = {
                'Authorization': 'Bearer ' + RestAPI.tokenObj['access_token'],
                'accept': 'application/vnd.allegro.public.v1+json',
                'content-type': 'application/vnd.allegro.public.v1+json'
            }

        if headers is not None:
            header.update(headers)

        for i in range(MAX_TRIES):
            req = requests.Request(method, resource,
                                   headers=header,
                                   data=data, json=json).prepare()

            log.debug('Prepared to send:')
            RestAPI.prettyLogRequest(req)

            s = requests.Session()

            resp = s.send(req)
            if 200 <= resp.status_code < 300:
                break
            elif resp.status_code == 401 and bearer is True:
                RestAPI.refreshAccessToken()
                header.update({'Authorization': 'Bearer ' + RestAPI.tokenObj['access_token']})

            time.sleep(5)

        respText = 'Response:\n' + \
                   pformat(resp.json())
        if resp.status_code < 200 or resp.status_code >= 300:
            raise ConnectionError(respText)

        log.debug(respText)

        return resp.json()

    @staticmethod
    def getDeliveryMethods():
        return RestAPI._rest('GET', 'https://api.allegro.pl/sale/delivery-methods', bearer=True)

    @staticmethod
    def getShippingRates():
        return RestAPI._rest('GET', 'https://api.allegro.pl/sale/shipping-rates?seller.id='
                             + RestAPI._getSellerID(), bearer=True)

    @staticmethod
    def getCategoryParams(categoryID):
        return RestAPI._rest('GET', 'https://api.allegro.pl/sale/categories/{}/parameters'.format(categoryID),
                             bearer=True)

    @staticmethod
    def getOffers(sellerID, phrase, limit=5):
        return RestAPI._rest('GET', 'https://api.allegro.pl/offers/listing?seller.id={}&phrase={}&limit={}'
                             .format(sellerID, phrase, limit), bearer=True)

    @staticmethod
    def getMyOffers(name=None, status='ACTIVE', limit=5):
        res = 'https://api.allegro.pl/sale/offers?publication.status={}&limit={}'.format(status, limit)
        if name is not None:
            res += '&name=' + name

        return RestAPI._rest('GET', res, bearer=True)

    @staticmethod
    def postImages(images):
        if not images:
            return

        links = list()
        for img in images:
            resp = RestAPI._rest('POST', 'https://api.allegro.pl/sale/images', json={'url': '{}'.format(img)},
                                 bearer=True)
            links.append(resp['location'])

        return links

    @staticmethod
    def getOfferDetails(offerID):
        return RestAPI._rest('GET', 'https://api.allegro.pl/sale/offers/{}'.format(offerID), bearer=True)

    @staticmethod
    def pushOffer(offerTemplate):
        log.debug('\n\nofferTemplate: json= \n\n'
                  '{}\n'.format(repr(offerTemplate)))

        resp = RestAPI._rest('POST', 'https://api.allegro.pl/sale/offers', json=offerTemplate, bearer=True)

        errors = resp['validation']['errors']
        if errors:
            raise IOError('errors:\n {}'.format(pformat(resp)))

        return resp

    @staticmethod
    def publish():
        pass
