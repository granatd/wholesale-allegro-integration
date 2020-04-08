import os
import logging as log
import traceback
import marketplaces.allegro.fileReader as Fr
from pprint import pformat
from wholesales.LuckyStar_nowegumy_pl.xmlParser import LuckyStarWholesale
from marketplaces.allegro.auctions import RestAPI, Auction
from marketplaces.allegro.integrations.LuckyStarProductIntegrator import LuckyStarProductIntegrator, WHEELS_COUNT

MAX_AUCTIONS_TO_SEND = 2500
ERROR_FILE_NAME = 'log/{}_wheels/auction.error'.format(WHEELS_COUNT)
LAST_AUCTION_FILE_NAME = 'log/{}_wheels/last_auction.log'.format(WHEELS_COUNT)

fmt = "[%(levelname)s:%(filename)s:%(lineno)s: %(funcName)s()] %(message)s"
log.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"), format=fmt)
log = log.getLogger(__name__)


def createLuckyStarWholesale():
    wholesale = LuckyStarWholesale()

    wholesale.filterProducts()
    wholesale.addOverhead(-8)

    return wholesale


def saveError(auctionNum, prodName):
    return Fr.saveObjToFile((prodName, traceback.format_exc()), ERROR_FILE_NAME + '.' + str(auctionNum))


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
        prodName, tb = Fr.readObjFromFile(ERROR_FILE_NAME)

        print('Found previous error log for \'{}\' product:\n\n'.format(prodName)
              + tb + '\n'
              + 'To run programme, please fix this error and remove \'{}\' file!\n'
              .format(ERROR_FILE_NAME))

        raise EnvironmentError('\nFIX ERRORS AND REMOVE \'{}\' FILE FIRST!'
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
        except IndexError:
            log.debug('No products left in a wholesale!')
            wholesale.toFirstProduct()
            break

        try:
            auction = Auction(integrator)

            auction.push()
            auction.saveOfferToFile()
            auction.publish()

            saveAuction(auction, lastAuctionNum + 1 + i)

        except Exception:
            saveError(lastAuctionNum + 1 + i, integrator.getTitle())

    Auction.handleCommandsStats()


if __name__ == '__main__':
    try:
        main()
    except Exception as ex:
        Auction.handleCommandsStats()

        if not isinstance(ex, EnvironmentError):
            raise

        print(str(ex))
