import os
import pickle
import traceback
import logging as log
from pprint import pformat
from wholesales.LuckyStar_nowegumy_pl.xmlParser import LuckyStarWholesale
from marketplaces.allegro.auctions import RestAPI, Auction
from marketplaces.allegro.integrations.LuckyStarProductIntegrator import LuckyStarProductIntegrator

ERROR_FILE_NAME = 'auction.error'
LAST_AUCTION_FILE_NAME = 'auction.log'

fmt = "[%(levelname)s:%(filename)s:%(lineno)s: %(funcName)s()] %(message)s"
log.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"), format=fmt)
log = log.getLogger(__name__)


def createLuckyStarWholesale():
    wholesale = LuckyStarWholesale()

    wholesale.filterProducts()
    wholesale.addOverhead(-8)

    return wholesale


def saveObjToFile(obj, file):
    with open(file, 'wb') as f:
        pickle.dump(obj, f)


def saveError(e):
    return saveObjToFile(e, 'auctionLastObj.error')


def saveAuction(auction, num):
    obj = dict()

    obj['num'] = num
    obj['auction'] = auction

    return saveObjToFile(obj, 'auctionLastObj.log')


def readObjFromFile(file):
    with open(file, 'rb') as f:
        return pickle.load(f)


def main():
    try:
        print('Starting diagnose mode...')

        lastAuction: Auction = readObjFromFile(LAST_AUCTION_FILE_NAME)
        print('Last successfull auction number: {}\n'
              'template:\n'
              '{}\n'.format(lastAuction['num'], lastAuction.getTemplate()))

        e = readObjFromFile(ERROR_FILE_NAME)
        print('Found previous error log traceback:')
        traceback.print_tb(e.__traceback__)
        print('\nTo run programme, please fix this error and remove \'{}\' file!'.format(ERROR_FILE_NAME))

        return
    except FileNotFoundError:
        print('No previous errors found!\n'
                  'Starting normal run...\n')

    RestAPI.deviceFlowOAuth()
    # RestAPI.getShippingRates()
    # RestAPI.getCategoryParams('257687')
    # RestAPI.getOfferDetails('9068419944')
    wholesale = createLuckyStarWholesale()
    for i in range(1):
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
        except Exception as e:
            saveError(e)

            if auction is not None:
                saveAuction(auction)
            raise e


if __name__ == '__main__':
    main()
