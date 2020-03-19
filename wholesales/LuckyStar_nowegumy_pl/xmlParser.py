import os
import requests
import logging as log
import xml.etree.ElementTree as eT

ns = {'ng': 'http://nowegumy.pl'}

log.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))
log = log.getLogger(__name__)


class LuckyStar:
    xmlFile = 'sklep.xml'
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
            self.fetchXML(self.xmlFile)

        self.root = eT.parse(self.xmlFile)
        self.products = self.root.findall('ng:PRODUKTY', ns)
        self.categories = self.root.findall('ng:KATEGORIE', ns)
        self.producers = self.root.findall('ng:PRODUCENCI', ns)

    def _getImages(self):
        photos = list()
        for desc in self.products.iter('ZDJECIA'):
            photos += desc['BIG'].text

        return photos

    def getImages(self):
        images = self._getImages()
        if len(images) < 1:
            log.debug('No image found!')

        return images

    def getDescValue(self, key):
        if key is None:
            raise LookupError('Key param is None! Means there is no corresponding param. in XML')

        for desc in self.products.iter('OPIS'):
            if desc['NAZWA'].text.lower() is key.lower():
                return desc['WARTOSC']

        raise LookupError('No {} field!'.format(key))

    def getType(self):
        return self.getDescValue('typ')

    def getSeason(self):
        return self.getDescValue('sezon')

    def getTitle(self):
        return self.products.find('ng:NAZWA', ns).text[0:49]

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
            price.text = str(float(price.text) * (percent/100))

