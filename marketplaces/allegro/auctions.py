import os
import re
import uuid
import time
import requests
import logging as log
from pprint import pformat
from base64 import b64encode, b64decode
import marketplaces.allegro.fileReader as Fr
from marketplaces.allegro.integrations.LuckyStarProductIntegrator import WHEELS_COUNT

MAX_TRIES = 2

ALLEGRO_TOKEN_FILE = 'allegro.token'
ALLEGRO_OFFERS_FILE = 'log/{}_wheels/allegro.offers'.format(WHEELS_COUNT)
ALLEGRO_OFFERS_STATUS_FILE = 'log/{}_wheels/allegro.offers.status'.format(WHEELS_COUNT)

fmt = "[%(levelname)s:%(filename)s:%(lineno)s: %(funcName)s()] %(message)s"
log.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"), format=fmt)
log = log.getLogger(__name__)

freeDelivery = {'id': 'cde2d24a-ab38-461d-96da-ade36d99e7cf'}
standardDelivery = {'id': 'a5805e2a-3613-406f-a91f-c924f944fa0b'}


class Auction:
    nextFreeNum = 1
    commandsIds = list()
    commandsStats = list()

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
                'handlingTime': 'P2D',
                'shippingRates': standardDelivery},
            'stock': {'available': None, 'unit': 'UNIT'},
            'category': {'id': None},
            'sellingMode': {'format': 'BUY_NOW',
                            'price': {'amount': None, 'currency': 'PLN'},
                            }
        }

        self.offer = None
        self.imgLinks = None
        self.restMod = RestAPI()
        self.integrator = integrator
        self.num = Auction.nextFreeNum
        self.incrementNextFreeNum()

        try:
            self.setEAN(integrator.getEAN())
        except LookupError as e:
            log.debug(repr(e))

        try:
            self.setImgLinks(integrator.getImages())
        except LookupError as e:
            log.debug(repr(e))

        self.setCategory(integrator.getCategory())
        self.setPrice(integrator.getPrice())
        self.setTitle(integrator.getTitle())
        self.setDeliveryShippingRates()
        self.setDescription(integrator.getDesc(self.imgLinks))
        self.setStockCount(integrator.getStockCount())
        self.setParams(integrator.getParams(self.getCategoryParams()))

        log.debug('\n\nCreated template:\n\n'
                  '{}'.format(pformat(self.template)))

    @staticmethod
    def setNextFreeNum(num):
        Auction.nextFreeNum = num

    @staticmethod
    def getStatus(cmdId):
        return RestAPI.getOfferStatus(cmdId)

    @staticmethod
    def getCommandsStats():
        try:
            log.debug('Searching old stats...')

            commandsStats = Fr.readObjFromFile(ALLEGRO_OFFERS_STATUS_FILE)
            commandsIds = [commandStat['id'] for commandStat in commandsStats]

            log.debug('Old stats found!\n'
                      'Refreshing old stats for commandsIds: {}'.format(commandsIds))

            Auction.commandsStats = [Auction.getStatus(cmdId) for cmdId in commandsIds]

        except FileNotFoundError:
            log.debug('Old stats not found!')

        if Auction.commandsIds:
            log.debug('Appending new commands stats for commandsIds: {}'.format(Auction.commandsIds))

            Auction.commandsStats += [Auction.getStatus(cmdId) for cmdId in Auction.commandsIds]

        if Auction.commandsStats:
            log.debug('All created stats:\n'
                      '{}'.format(pformat(Auction.commandsStats)))

    @staticmethod
    def saveNotFinishedCommands():

        notFinishedCmds = [
            commandStat for commandStat in Auction.commandsStats if commandStat['taskCount']['success'] == 0
        ]

        if not notFinishedCmds:
            if os.path.exists(ALLEGRO_OFFERS_STATUS_FILE):
                os.remove(ALLEGRO_OFFERS_STATUS_FILE)
            return

        Fr.saveObjToFile(notFinishedCmds, ALLEGRO_OFFERS_STATUS_FILE)

        log.debug('Stats successfully saved to \'{}\' file!'.format(ALLEGRO_OFFERS_STATUS_FILE))

    @staticmethod
    def printCommandsStats():
        if not Auction.commandsStats:
            return

        print('\nCommandsStats [{}]:\n'
              '{}\n'.format(len(Auction.commandsStats), pformat(Auction.commandsStats)))

    @staticmethod
    def handleCommandsStats():
        Auction.getCommandsStats()
        Auction.saveNotFinishedCommands()
        Auction.printCommandsStats()

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

    def publish(self):
        commandId = self.restMod.publishOffer(self.offer['id'])
        Auction.commandsIds.append(commandId)

    def getTemplate(self):
        return self.template

    def getCategoryParams(self):
        return self.restMod.getCategoryParams(self.integrator.getCategory()['id'])

    def setDeliveryShippingRates(self):
        if WHEELS_COUNT == 4:
            self.template['delivery']['shippingRates'] = freeDelivery


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

        if RestAPI.tokenObj is not None:
            return

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

        def decode_base64(data, altchars=b'+/'):
            """Decode base64, padding being optional.

            :param data: Base64 data as an ASCII byte string
            :returns: The decoded byte string.

            """
            data = re.sub(rb'[^a-zA-Z0-9%s]+' % altchars, b'', data)  # normalize
            missing_padding = len(data) % 4
            if missing_padding:
                data += b'=' * (4 - missing_padding)
            return b64decode(data, altchars)

        b64_string = RestAPI.tokenObj['access_token'].encode()
        matchObj = re.search(b'\"user_name\":\"([0-9]+)\"', decode_base64(b64_string), re.IGNORECASE)
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
        RestAPI.deviceFlowOAuth()
        return RestAPI._rest('GET', 'https://api.allegro.pl/sale/shipping-rates?seller.id='
                             + RestAPI._getSellerID(), bearer=True)

    @staticmethod
    def getCategoryParams(categoryID):
        return RestAPI._rest('GET', 'https://api.allegro.pl/sale/categories/{}/parameters'.format(categoryID),
                             bearer=True)

    @staticmethod
    def _getCategoriesPathDetails(path, parent):
        assert(path is not None and parent is not None)

        if not path:
            return [parent]

        currName = path[0]
        subcategories = path[1:]

        for category in parent['categories']:
            if re.search(currName, category['name'], re.IGNORECASE) or \
                    re.search(category['name'], currName, re.IGNORECASE):

                parent = RestAPI._rest('GET', 'https://api.allegro.pl/sale/categories?parent.id={}'
                                       .format(category['id']), bearer=True)
                categories = RestAPI._getCategoriesPathDetails(subcategories, parent)
                categories.insert(0, parent)
                return categories

    @staticmethod
    def getRootCategory():
        return RestAPI._rest('GET', 'https://api.allegro.pl/sale/categories', bearer=True)

    @staticmethod
    def getCategoriesPathDetails(path=None):
        RestAPI.deviceFlowOAuth()

        root = RestAPI.getRootCategory()

        if path is None:
            return [root]

        return RestAPI._getCategoriesPathDetails(path, root)

    @staticmethod
    def printCategoriesPathDetails(path=None):
        details = RestAPI.getCategoriesPathDetails(path)

        for cat in details:
            print(pformat(cat))
            print('----------------------------------------------------------------------')

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
    def getOfferStatus(cmdId):
        return RestAPI._rest('GET', 'https://api.allegro.pl/sale/offer-publication-commands/{}'.format(cmdId),
                             bearer=True)

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
    def publishOffer(draftId):
        template = {
            "publication": {
                "action": "ACTIVATE",  # wymagane, dostępne są dwie wartości:
                # - ACTIVATE(aktywowanie danych ofert) i
                # - END(zakończenie danych ofert)
                # "scheduledFor": "2018-03-28T12:00:00.000Z"    # niewymagane, wysyłasz jeśli chcesz
                # zaplanować wystawienie oferty w przyszłości
            },
            "offerCriteria": [
                {
                    "offers": [  # wymagane, tablica obiektów z numerami identyfikacyjnymi ofert - max 1000 ofert
                        {
                            "id": ""
                        }
                    ],
                    "type": "CONTAINS_OFFERS"  # wymagane, obecnie dostępna jest jedna wartość:
                    # CONTAINS_OFFERS(oferty, w których zmienimy status)
                }
            ]
        }

        log.debug('Publishing \'{}\' offer...'.format(draftId))

        commandId = uuid.uuid4()
        template['offerCriteria'][0]['offers'][0]['id'] = draftId

        RestAPI._rest('PUT', 'https://api.allegro.pl/sale/offer-publication-commands/{}'.format(commandId),
                      json=template, bearer=True)

        return commandId
