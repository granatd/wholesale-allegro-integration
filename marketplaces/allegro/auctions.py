import os
import re
import time
import pickle
import logging as log
import requests
from pprint import pformat
from base64 import b64encode, b64decode

fmt = "[%(levelname)s:%(filename)s:%(lineno)s: %(funcName)s()] %(message)s"
log.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"), format=fmt)
log = log.getLogger(__name__)


class Auction:
    def __init__(self, integrator):
        self.template = {
            'additionalServices': None,
            'afterSalesServices': {'impliedWarranty': {'id': '95b451bf-7fd6-4d46-9bc1-ac6516eeb065'},
                                   'returnPolicy': {'id': 'f7b5005b-4b46-45d7-bab8-e17208729f2c'},
                                   'warranty': {'id': '593b3ed0-655c-40e6-acbc-7782351cca75'}},
            'attachments': None,
            'category': None,
            'compatibilityList': None,
            'contact': None,
            'delivery': {'additionalInfo': None,
                         'handlingTime': 'PT24H',
                         'shipmentDate': None,
                         'shippingRates': {'id': 'cde2d24a-ab38-461d-96da-ade36d99e7cf'}},
            'description': None,
            'ean': None,
            'images': None,
            'location': {'city': 'Łódź',
                         'countryCode': 'PL',
                         'postCode': '90-619',
                         'province': 'LODZKIE'},
            'name': None,
            'parameters': None,
            'payments': {'invoice': 'VAT'},
            'product': None,
            'publication': {'duration': None,
                            'endedBy': None,
                            'endingAt': None,
                            'republish': True,
                            'startingAt': None,
                            'status': 'ACTIVE'},
            'sellingMode': {'format': 'BUY_NOW',
                            'minimalPrice': None,
                            'price': {'amount': None, 'currency': 'PLN'},
                            'startingPrice': None},
            'sizeTable': None,
            'stock': {'available': 2, 'unit': 'UNIT'},
        }

        self.restMod = RestAPI()
        self.integrator = integrator

        self.prodCategory = integrator.getCategory()
        self.prodCategoryParams = self.restMod.getCategoryParams(self.prodCategory)

        self.setCategory(self.prodCategory)
        self.setPrice(integrator.getPrice())
        self.setTitle(integrator.getTitle())
        self.setImages(integrator.getImages())
        self.setDescription(integrator.getDesc())
        self.setStockCount(integrator.getStockCount())
        self.setParams(integrator.getParams(self.prodCategoryParams))

        log.debug('\n\nCreated template:\n\n'
                  '{}'.format(pformat(self.template)))

    def setTitle(self, name):
        self.template['name'] = name

    def setImages(self, images):
        self.template['images'] = images

    def setCategory(self, category):
        self.template['category'] = str(category)

    def setDescription(self, desc):
        self.template['description'] = desc

    def setParams(self, params):
        self.template['parameters'] = params

    def setStockCount(self, count):
        self.template['stock'] = str(count)

    def setPrice(self, price):
        self.template['sellingMode']['price'] = price


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
        with open('allegro.token', 'rb') as tokenFile:
            RestAPI.tokenObj = pickle.load(tokenFile)

        return RestAPI.tokenObj

    @staticmethod
    def saveToken(tokenObj):
        with open('allegro.token', 'wb') as tokenFile:
            pickle.dump(tokenObj, tokenFile)

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
        matchObj = re.search(b'\"user_name\":\"([0-9]+)\"', b64decode(b64_string))
        sellerID = matchObj.group(1).decode("UTF-8")
        log.debug(sellerID)

        return sellerID

    @staticmethod
    def _rest(method, resource, bearer=False, headers=None, data=None):
        header = dict()

        if bearer is True:
            header = {
                'Authorization': 'Bearer ' + RestAPI.tokenObj['access_token'],
                'accept': 'application/vnd.allegro.public.v1+json',
                'content-type': 'application/vnd.allegro.public.v1+json'
            }

        if headers is not None:
            header.update(headers)

        for i in range(3):
            req = requests.Request(method, resource,
                                   headers=header,
                                   data=data).prepare()
            RestAPI.prettyLogRequest(req)

            s = requests.Session()

            resp = s.send(req)
            if resp.status_code == 200:
                break
            elif resp.status_code == 401 and bearer is True:
                RestAPI.refreshAccessToken()
                header.update({'Authorization': 'Bearer ' + RestAPI.tokenObj['access_token']})

            time.sleep(5)

        respText = 'Response:\n' + \
                   pformat(resp.json())
        if resp.status_code is not 200:
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
        if len(images) < 1:
            return

        RestAPI._rest('POST', 'https://api.allegro.pl/sale/images',
                      data={
                          'url': '{}'.format(img) for img in images
                      })

    @staticmethod
    def getOfferDetails(offerID):
        return RestAPI._rest('GET', 'https://api.allegro.pl/sale/offers/{}'.format(offerID), bearer=True)

    @staticmethod
    def push():
        resp = RestAPI._rest('POST', 'https://api.allegro.pl/sale/offers', data=RestAPI.template, bearer=True)
        errors = resp['validation']['errors']
        if errors:
            raise IOError('errors:\n {}'.format(repr(errors)))

    @staticmethod
    def publish():
        pass
