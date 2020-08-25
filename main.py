import os
import re
import shutil
import logging as log
import traceback
import marketplaces.allegro.fileReader as Fr
from pprint import pformat
from logs import LogFiles
from wholesales.LuckyStar_nowegumy_pl.xmlParser import LuckyStarWholesale
from marketplaces.allegro.allegro import Allegro
from marketplaces.allegro.integrations.LuckyStarProductIntegrator import LuckyStarProductIntegrator

PRICE_OVERHEAD = -8  # percents
MAX_AUCTIONS_TO_SEND = 2

fmt = "[%(levelname)s:%(filename)s:%(lineno)s: %(funcName)s()] %(message)s"
log.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"), format=fmt)
log = log.getLogger(__name__)


class Prog:
    @staticmethod
    def createLuckyStarWholesale():
        wholesale = LuckyStarWholesale()

        wholesale.filterProducts()
        wholesale.addOverhead(PRICE_OVERHEAD)

        return wholesale

    wholesale = createLuckyStarWholesale()
    nextFreeNum = 0
    logFiles = LogFiles
    auction = None
    productNum = None
    prodName = None
    allegro = None

    @staticmethod
    def saveError():
        assert Prog.prodName is not None and Prog.productNum is not None \
               and Prog.logFiles is not None

        logsDir = Prog.logFiles.logsDir

        return Fr.saveObjToFile((Prog.prodName, traceback.format_exc()),
                                logsDir + '/' + Prog.logFiles.errorFileName + '.' + str(Prog.productNum))

    @staticmethod
    def saveLastAuction():
        assert Prog.productNum is not None and Prog.auction is not None

        obj = dict()

        obj['num'] = Prog.productNum
        obj['auction'] = Prog.auction

        return Fr.saveObjToFile(obj, LogFiles.lastAuctionFilePath + '.' + str(Prog.productNum))

    @staticmethod
    def saveAuction():
        assert Prog.productNum is not None and Prog.auction is not None \
               and Prog.logFiles is not None

        obj = dict()

        obj['num'] = Prog.productNum
        obj['auction'] = Prog.auction

        return Fr.saveObjToFile(obj, Prog.logFiles.auctionFilePath + '.' + str(Prog.productNum))

    @staticmethod
    def setAuctionNum(num):
        Prog.productNum = num
        Allegro.auction.setAuctionNum(num)

    @staticmethod
    def handleLastErrors():
        assert Prog.logFiles is not None

        try:
            print('Starting diagnose mode...')

            lastAuctionNum = None
            lastAuction = None
            lastObj = Fr.readObjFromFile(LogFiles.lastAuctionFilePath)

            if lastObj is not None:
                lastAuctionNum = lastObj['num']
                lastAuction = lastObj['auction']

            print('Last successful auction number: {}\n'
                  'Auction:\n'
                  '{}\n'.format(lastAuctionNum, pformat(lastAuction.getTemplate())))

        except FileNotFoundError:
            lastAuctionNum = 0

        logNums = [int(os.path.splitext(f)[1][1:]) for f in os.listdir(Prog.logFiles.logsDir)
                   if re.match(rf'{LogFiles.errorFileName}.[0-9]+', f)]

        if not logNums:
            print('No previous errors found!\n'
                  'Starting normal run...\n')

            return lastAuctionNum

        logNums.sort()
        num = input("Found error logs, pick log nr to show or '0' to skip:\n\n"
                    "{}:\n".format(logNums))

        if int(num) == 0:
            return lastAuctionNum

        errFilePath = Prog.logFiles.logsDir + '/' + LogFiles.errorFileName + '.' + str(num)
        prodName, tb = Fr.readObjFromFile(errFilePath)

        print('Error log for \'{}\' product:\n\n'.format(prodName)
              + tb + '\n')

        raise EnvironmentError('Normal run aborted')

    @staticmethod
    def cleanLuckyStarWholesaleLogFiles():
        shutil.rmtree(LogFiles.logsDir)

    @staticmethod
    def incrementProductNum():
        Prog.productNum += 1

    @staticmethod
    def createAuctions(productsLeft):

        for i in range(productsLeft):
            try:
                Prog.incrementProductNum()
                prod = Prog.wholesale.getProduct()
                integrator = LuckyStarProductIntegrator(prod)
            except IndexError:
                log.debug('No products left in a wholesale!')
                Prog.wholesale.toFirstProduct()
                return productsLeft - i

            try:
                name = integrator.getTitle()
                cat = integrator.getCategory()['id']
                if Prog.allegro.isDuplicatedOffer(name, cat):
                    log.debug('Skipping duplicated offer[{}]:\n'.format(Prog.productNum) +
                              pformat(Prog.allegro.auction))
                    continue

                Prog.allegro.createAuction(integrator)

                Prog.allegro.auction.push()
                Prog.allegro.auction.publish()

                Prog.saveAuction()

            except Exception:
                Prog.saveError()

    @staticmethod
    def skipProducts(lastProduct):
        for i in range((lastProduct - 1) % Prog.wholesale.getProductsCount() + 1):
            Prog.wholesale.getProduct()

    @staticmethod
    def main():
        try:
            Prog.allegro = Allegro()
            Prog.allegro.restAPI.deviceFlowOAuth()

            lastAuctionNum = Prog.handleLastErrors()
            Prog.setAuctionNum(lastAuctionNum)

            if Prog.wholesale.hasNewData():
                Prog.cleanLuckyStarWholesaleLogFiles()

            Prog.skipProducts(lastAuctionNum)

            Prog.createAuctions(MAX_AUCTIONS_TO_SEND)

            Allegro.auction.handleCommandsStats()

        except Exception as ex:
            Allegro.auction.handleCommandsStats()

            if not isinstance(ex, EnvironmentError):
                raise

            print(str(ex))


if __name__ == '__main__':
    Prog.main()
