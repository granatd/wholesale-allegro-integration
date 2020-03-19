import os
import logging as log
from marketplaces.allegro.auctions import RestAPI

log.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))
log = log.getLogger(__name__)


def createAllegroProducts():

    try:
        allegroProducts += AllegroTire(prod)
    except (LookupError, ValueError) as e:
        log.debug(repr(e))
        continue

    return allegroProducts


def main():
    RestAPI.deviceFlowOAuth()
    # RestAPI.getShippingRates()
    # RestAPI.getCategoryParams('257687')
    products = createProductParams('/home/daniel/Documents/1_praca/1_Freelance/1_handel/'
                                      '1_allegro/1_sklepy/LuckyStar/sklep.xml')
    prod = products.pop()

    # RestAPI.getOfferDetails('9068419944')

    auction = Auction(prod)
    auction.allegroPost()


if __name__ == '__main__':
    main()
