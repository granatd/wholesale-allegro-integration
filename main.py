import os
import logging as log
from wholesales.LuckyStar_nowegumy_pl.xmlParser import LuckyStar
from marketplaces.allegro.auctions import RestAPI, Auction
from marketplaces.allegro.integrations.LuckyStarProductIntegrator import LuckyStarProductIntegrator

log.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))
log = log.getLogger(__name__)


def LuckyStarProducts():
    products = LuckyStar()

    products.filterProducts()
    products.addOverhead(-8)

    return products


def main():
    RestAPI.deviceFlowOAuth()
    # RestAPI.getShippingRates()
    # RestAPI.getCategoryParams('257687')
    # RestAPI.getOfferDetails('9068419944')
    products = LuckyStarProducts()
    prod = products.getProduct()
    integrator = LuckyStarProductIntegrator(prod)

    auction = Auction(integrator)
    auction.push()


if __name__ == '__main__':
    main()
