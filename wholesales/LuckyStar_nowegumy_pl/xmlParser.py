import os
import re
import requests
import logging as log
import xml.etree.ElementTree as eT

MIN_STOCK_COUNT = 10
MIN_PRICE_ZL = 100

ns = {'ng': 'http://nowegumy.pl'}

fmt = "[%(levelname)s:%(filename)s:%(lineno)s: %(funcName)s()] %(message)s"
log.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"), format=fmt)
log = log.getLogger(__name__)


class LuckyStarWholesale:

    def __init__(self):
        self.xmlFile = 'sklep.xml'
        if not os.path.isfile(self.xmlFile):
            self._fetchXML()

        self.product = None
        self.productIdx = 0

        self.tree = eT.parse(self.xmlFile)
        self.root = self.tree.getroot()
        self.products = self.root.find('ng:PRODUKTY', ns).findall('ng:PRODUKT', ns)
        self.categories = self.root.find('ng:KATEGORIE', ns).findall('ng:KATEGORIA', ns)
        self.producers = self.root.find('ng:PRODUCENCI', ns).findall('ng:PRODUCENT', ns)

    def _fetchXML(self):
        url = 'https://xml.nowegumy.pl/38c07d9eb6f585cb2e363aa8d83443b1b9fcc722/sklep.xml'
        resp = requests.get(url)

        with open('sklep.xml', 'wb') as f:
            f.write(resp.content)

    def isFiltered(self, prod):
        state = prod.find('ng:STAN', ns)
        count = state.text

        if int(count) < MIN_STOCK_COUNT:
            return False

        price = prod.find('ng:CENA_BRUTTO', ns)
        if price.text is None or float(price.text) < MIN_PRICE_ZL:
            return False

        return True

    def filterProducts(self):
        self.products = [prod for prod in self.products if self.isFiltered(prod)]

    def addOverhead(self, percent):
        """Dodaje narzut procentowy do ceny zakupu"""

        products = self.products

        for prod in products:
            price = prod.find('ng:CENA_BRUTTO', ns)
            price.text = str(float(price.text) * (1 + percent/100))

            price = prod.find('ng:CENA_NETTO', ns)
            price.text = str(float(price.text) * (1 + percent / 100))

    def toFirstProduct(self):
        self.productIdx = 0

    def getProductIdx(self):
        return self.productIdx

    def getProduct(self):
        self.product = LuckyStarProduct(self.products[self.productIdx])
        self.productIdx += 1

        return self.product


class LuckyStarProduct:
    def __init__(self, xmlProduct):
        self.product = xmlProduct

    def _getImages(self):
        photos = list()
        for desc in self.product.iter('{' + ns['ng'] + '}' + 'ZDJECIA'):
            photos.append(desc.find('ng:BIG', ns).text)

        return photos

    def getImages(self):
        images = self._getImages()
        if len(images) < 1:
            log.debug('No image found!')

        return images

    def getPrice(self):
        return self.product.find('ng:CENA_BRUTTO', ns).text

    def getTitle(self):
        return self.product.find('ng:NAZWA', ns).text

    def getStockCount(self):
        return self.product.find('ng:STAN', ns).text

    def getDescValue(self, key):
        if key is None:
            raise LookupError('Key param is None! Means there is no corresponding param. in XML')

        for desc in self.product.iter('{' + ns['ng'] + '}' + 'OPIS'):
            if desc.find('ng:NAZWA', ns).text.lower() == key.lower():
                return desc.find('ng:WARTOSC', ns).text

        raise LookupError('{}'.format(key))

    def getType(self):
        return self.getDescValue('Typ')

    def getSeason(self):
        return self.getDescValue('Sezon')

    def getProducer(self):
        return self.getDescValue('Producent')

    def getModel(self):
        return self.getDescValue('Nazwa')

    def getSize(self):
        return self.getDescValue('Rozmiar')

    def getWidth(self):
        return self.getDescValue('Szerokość')

    def getHeight(self):
        return self.getDescValue('Wysokość')

    def getRimSize(self):
        return self.getDescValue('Rozmiar felgi')

    def getVmax(self):
        return self.getDescValue('Indeks prędkości')

    def getLoadIndex(self):
        return self.getDescValue('Indeks nośności')

    def getProducerCode(self):
        return self.getDescValue('Kod producenta')

    def getEAN(self):
        return self.getDescValue('EAN')

    def getDestination(self):
        return self.getDescValue('Identyfikator')

    def getWeight(self):
        return self.getDescValue('Waga')

    def getVolumeSize(self):
        return self.getDescValue('Objętość')

    def getRotationResistance(self):
        return self.getDescValue('Opory toczenia')

    def getWetTraction(self):
        return self.getDescValue('Hamowanie na mokrym')

    def getNoiseLevel(self):
        return self.getDescValue('Poziom hałasu')

    def getOverallInfo(self):
        return self.getDescValue('Informacje ogólne')

    def getWarranty(self):
        return self.getDescValue('Gwarancja')

    def getProducerInfo(self):
        return self.getDescValue('O ' + self.getProducer())

    def getCompatibleModelsDesc(self):
        return self.getDescValue('Pasuje do')

    def getAdditionalDescription(self):

        def isOverMinLength(desc):
            minChars = 80
            descValue = desc.find('ng:WARTOSC', ns).text

            return len(descValue) > minChars

        # def replaceForbiddenHTMLtags(desc):
        #     descValue = desc.find('ng:WARTOSC', ns)
        #     descValueText = descValue.text
        #     forbiddenTags = ['<a href=(.+)>', '<img src=(.+)>', '</a>',]
        #
        #     re.search


        def keywordsMatch(desc):
            includedKeys = [r'\bO\b']
            excludedKeys = ['Informacje ogólne', 'Pasuje do', ]

            descName = desc.find('ng:NAZWA', ns).text

            for includedKey in includedKeys:
                if re.search(includedKey, descName, re.IGNORECASE):
                    return True

            for excludedKey in excludedKeys:
                if re.search(excludedKey, descName, re.IGNORECASE):
                    return False

        def isAdditionalDescription(desc):
            validators = [keywordsMatch, ]

            validators.append(isOverMinLength)

            for validator in validators:
                validity = validator(desc)
                if validity is not None:
                    return validity

            return False

        descriptions = list()

        for desc in self.product.iter('{' + ns['ng'] + '}' + 'OPIS'):
            descName = desc.find('ng:NAZWA', ns).text
            descValue = desc.find('ng:WARTOSC', ns).text

            if isAdditionalDescription(desc):
                descriptions.append((descName, descValue))

        return descriptions
