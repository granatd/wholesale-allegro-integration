import os
import requests
import logging as log
import xml.etree.ElementTree as eT

ns = {'ng': 'http://nowegumy.pl'}

fmt = "[%(levelname)s:%(filename)s:%(lineno)s: %(funcName)s()] %(message)s"
log.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"), format=fmt)
log = log.getLogger(__name__)


class LuckyStarWholesale:
    xmlFile = 'sklep.xml'
    product = None
    products = list()
    categories = list()
    producers = list()

    def fetchXML(self):
        url = 'https://xml.nowegumy.pl/38c07d9eb6f585cb2e363aa8d83443b1b9fcc722/sklep.xml'
        resp = requests.get(url)

        with open('sklep.xml', 'wb') as f:
            f.write(resp.content)

    def __init__(self):
        if not os.path.isfile(self.xmlFile):
            self.fetchXML()

        self.tree = eT.parse(self.xmlFile)
        self.root = self.tree.getroot()
        self.products = self.root.find('ng:PRODUKTY', ns).findall('ng:PRODUKT', ns)
        self.categories = self.root.find('ng:KATEGORIE', ns).findall('ng:KATEGORIA', ns)
        self.producers = self.root.find('ng:PRODUCENCI', ns).findall('ng:PRODUCENT', ns)

    def filterProducts(self):
        products = self.products

        for prod in products:
            state = prod.find('ng:STAN', ns)
            count = state.text
            if int(count) < 5:
                continue

            price = prod.find('ng:CENA_BRUTTO', ns)
            if price.text is None:
                continue

    def addOverhead(self, percent):
        """Dodaje narzut procentowy do ceny zakupu"""

        products = self.products

        for prod in products:
            price = prod.find('ng:CENA_BRUTTO', ns)
            price.text = str(float(price.text) * (1 + percent/100))

    def getProduct(self):
        self.product = LuckyStarProduct(self.products.pop())
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

    def getTitle(self):
        return self.product.find('ng:NAZWA', ns).text[0:49]

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
