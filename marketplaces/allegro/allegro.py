from marketplaces.allegro.auctions import Auction
from marketplaces.allegro.auctions import RestAPI


class Allegro:
    auction = Auction
    restAPI = RestAPI

    def __init__(self):
        self.auction = None
        self.filteredOffers = None

    def createAuction(self, integrator):
        self.auction = Auction(integrator)

    def filterMyOffers(self, name=None, status='ACTIVE', limit=5, categoryId=None):
        self.filteredOffers = RestAPI.getMyOffers(name, status, limit)['offers']
        if not categoryId or not self.filteredOffers:
            return self.filteredOffers

        self.filteredOffers = [offer for offer in self.filteredOffers if offer['category']['id'] == categoryId]

        return self.filteredOffers

    def isDuplicatedOffer(self, name, categoryId):
        return self.filterMyOffers(name, 'ACTIVE', 1, categoryId)
