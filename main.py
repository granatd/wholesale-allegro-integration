import os
import logging as log
from pprint import pformat
from wholesales.LuckyStar_nowegumy_pl.xmlParser import LuckyStarWholesale
from marketplaces.allegro.auctions import RestAPI, Auction
from marketplaces.allegro.integrations.LuckyStarProductIntegrator import LuckyStarProductIntegrator

fmt = "[%(levelname)s:%(filename)s:%(lineno)s: %(funcName)s()] %(message)s"
log.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"), format=fmt)
log = log.getLogger(__name__)


def createLuckyStarWholesale():
    wholesale = LuckyStarWholesale()

    wholesale.filterProducts()
    wholesale.addOverhead(-8)

    return wholesale


def main():
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
            # log.debug(pformat(integrator.getDesc()))
            auction = Auction(integrator)
        except ValueError as e:
            log.debug('Auction creation error:\n'
                      '{}'.format(repr(e)))
            continue

        auction.push()


if __name__ == '__main__':
    main()
