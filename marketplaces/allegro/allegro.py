from marketplaces.allegro.auctions import Auction
from marketplaces.allegro.auctions import RestAPI


class Allegro:
    auction = Auction
    restAPI = RestAPI

    def __init__(self):
        self.auction = None

    def createAuction(self, integrator):
        self.auction = Auction(integrator)

    @staticmethod
    def filterMyOffers(name=None, status='ACTIVE', limit=5, categoryId=None):
        filteredOffers = RestAPI.getMyOffers(name, status, limit)
        if categoryId is None:
            return filteredOffers

        return [offer for offer in filteredOffers['offers'] if offer['category']['id'] == categoryId]
