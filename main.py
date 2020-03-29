import os
import logging as log
import marketplaces.allegro.fileReader as Fr
from pprint import pformat
from wholesales.LuckyStar_nowegumy_pl.xmlParser import LuckyStarWholesale
from marketplaces.allegro.auctions import RestAPI, Auction
from marketplaces.allegro.integrations.LuckyStarProductIntegrator import LuckyStarProductIntegrator

ERROR_FILE_NAME = 'log/auction.error'
LAST_AUCTION_FILE_NAME = 'log/last_auction.log'
MAX_AUCTIONS_TO_SEND = 100

fmt = "[%(levelname)s:%(filename)s:%(lineno)s: %(funcName)s()] %(message)s"
log.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"), format=fmt)
log = log.getLogger(__name__)


def createLuckyStarWholesale():
    wholesale = LuckyStarWholesale()

    wholesale.filterProducts()
    wholesale.addOverhead(-8)

    return wholesale


def saveError(e):
    return Fr.saveObjToFile(e, ERROR_FILE_NAME)


def saveAuction(auction, num):
    obj = dict()

    obj['num'] = num
    obj['auction'] = auction

    return Fr.saveObjToFile(obj, LAST_AUCTION_FILE_NAME)


def handleLastErrors():
    try:
        print('Starting diagnose mode...')

        lastAuctionNum = None
        lastAuction = None
        lastObj = Fr.readObjFromFile(LAST_AUCTION_FILE_NAME)

        if lastObj is not None:
            lastAuctionNum = lastObj['num']
            lastAuction = lastObj['auction']

        print('Last successfull auction number: {}\n'
              'Auction:\n'
              '{}\n'.format(lastAuctionNum, pformat(lastAuction.getTemplate())))

    except FileNotFoundError:
        lastAuctionNum = 0

    Auction.setNextFreeNum(lastAuctionNum + 1)

    try:
        e = Fr.readObjFromFile(ERROR_FILE_NAME)

        print('Found previous error log:\n' + str(e))

        raise EnvironmentError('\nTo run programme, please fix this error and remove \'{}\' file!'
                               .format(ERROR_FILE_NAME))

    except FileNotFoundError:
        print('No previous errors found!\n'
              'Starting normal run...\n')

        return lastAuctionNum


def main():
    RestAPI.deviceFlowOAuth()

    lastAuctionNum = handleLastErrors()

    wholesale = createLuckyStarWholesale()

    for i in range(lastAuctionNum):  # skip already sent products
        wholesale.getProduct()

    for i in range(MAX_AUCTIONS_TO_SEND):
        try:
            prod = wholesale.getProduct()
            integrator = LuckyStarProductIntegrator(prod)
        except IndexError as e:
            log.debug('No products left in a wholesale!')
            wholesale.toFirstProduct()
            break

        try:
            auction = Auction(integrator)

            auction.push()
            auction.saveOfferToFile()
            auction.publish()

            saveAuction(auction, lastAuctionNum + 1 + i)

        except Exception as e:
            saveError(e)
            raise

    Auction.handleCommandsStatus()


if __name__ == '__main__':
    try:
        main()
    except Exception:
        Auction.handleCommandsStatus()
        raise
