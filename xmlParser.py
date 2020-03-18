import os
import requests
import logging as log
import xml.etree.ElementTree as eT

ns = {'ng': 'http://nowegumy.pl'}

log.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))
log = log.getLogger(__name__)


allegro2ngMap = {
    'Marka': 'Producent',
    'Model': None,
    'Kod producenta': 'Kod producenta',
    'Szerokość opony': 'Szerokość',
    'Profil opony': 'Wysokość',
    'Średnica': 'Rozmiar felgi',
    'Rok produkcji': None,
    'Indeks prędkości': 'Indeks prędkości',
    'Indeks nośności': 'Indeks nośności',
    'Opór toczenia': 'Opory toczenia',
    'Przyczepność na mokrej nawierzchni': 'Hamowanie na mokrym',
    'Hałas zewnętrzny': 'Poziom hałasu',
    'Rodzaj': 'Rodzaj',
    'Sezon': 'Indentyfikator',
    'Waga (z opakowaniem)': 'Waga',
    #'Bieżnik': 'Głębokość bieżnika [mm]',
    #'Przeznaczenie': 'Typ', # np. terenowe, zimowe, autobus
    # 'Rodzaj': 'Opis -> bezdętkowa',  # np. bez/dętkowe
    #  'Oś': None, # np. prowadząca, napędowa, naczepowa, uniwersalna
    #  'Liczba płócien (PR)': 'Opis-> warstwowa',
    # 'Konstrukcja': 'Opis/Informacje ogólne/Przeznaczenie/Techniczne cechy opony -> radialna, diagonalna',
    'Typ motocykla': None,
    'informacje dodatkowe': None,
}


def fetchXML():
    url = 'https://xml.nowegumy.pl/38c07d9eb6f585cb2e363aa8d83443b1b9fcc722/sklep.xml'
    resp = requests.get(url)

    with open('sklep.xml', 'wb') as f:
        f.write(resp.content)


class AllegroTire:
    __ngProd = None
    __availableParams = None
    __paramsToSet = None

    def getWholesaleImages(self):
        photos = list()
        for desc in self.__ngProd.iter('ZDJECIA'):
            photos += desc['BIG'].text

        return photos

    def getValue(self, key):
        if key is None:
            raise LookupError('Key param is None! Means there is no corresponding param. in XML')

        for desc in self.__ngProd.iter('OPIS'):
            if desc['NAZWA'].text.lower() is key.lower():
                return desc['WARTOSC']

        raise LookupError('No {} field!'.format(key))

    def getType(self):
        return self.getValue('typ')

    def getSeason(self):
        return self.getValue('sezon')

    def getTitle(self):
        return self.__ngProd.find('ng:NAZWA', ns).text[0:49]

    def getAllegroCategory(self):
        if self.getType() == 'samochody osobowe':
            if self.getSeason() is None:
                return '257689'
            elif self.getSeason() == 'letnie':
                return '257689'
            elif self.getSeason() == 'całoroczne':
                return '257692'
        elif self.getType() == 'samochody terenowe, SUV, Pickup':
            if self.getSeason() is None:
                return '257694'
            elif self.getSeason() == 'letnie':
                return '257694'
            elif self.getSeason() == 'całoroczne':
                return '257696'
        elif self.getType() == 'samochody dostawcze':
            if self.getSeason() is None:
                return '257698'
            elif self.getSeason() == 'letnie':
                return '257698'
            elif self.getSeason() == 'całoroczne':
                return '257700'
        elif self.getType() == 'przemysłowe':
            if self.getSeason() is None:
                return None
            elif self.getSeason() == 'letnie':
                return None
            elif self.getSeason() == 'całoroczne':
                return None

        raise ValueError('Value not found!')

    def assignParams(self):
        self.__availableParams['parameters'] = list()
        self.__paramsToSet['parameters'] = list()

        availableParams = self.__availableParams['parameters']
        params = self.__paramsToSet['parameters']

        for param in availableParams:
            try:
                if param['name'].lower() == 'stan' or \
                        param['name'].lower() == 'liczba opon w ofercie':
                    params += {
                        'id': param['id'],
                        'valuesIds': [
                            param['dictionary'][0]['id'],
                        ],
                        'values': [],
                        'rangeValue': None
                    }
                elif (param['type'] is 'float' or
                        param['type'] is 'int') and \
                            param['restrictions']['range'] is False:
                    val = float(self.getValue(allegro2ngMap[param['name']]))
                    if val < param['restrictions']['min']:
                        val = param['restrictions']['min']
                    elif val > param['restrictions']['max']:
                        val = param['restrictions']['max']

                    params += {
                        'id': param['id'],
                        'valuesIds': [],
                        'values': val,
                        'rangeValue': None
                    }
                elif param['type'] is 'string':
                    params += {
                        'id': param['id'],
                        'valuesIds': [],
                        'values': self.getValue(allegro2ngMap[param['name']]),
                        'rangeValue': None
                    }
            except LookupError as e:
                log.debug(repr(e))
                continue

    def getAvailableParams(self, categoryID):
        self.__availableParams = getCategoryParams(categoryID)

    def __init__(self, ngProduct):
        self.__ngProd = ngProduct
        categoryID = self.getAllegroCategory()
        self.getAvailableParams(categoryID)
        self.assignParams()


def createAllegroProducts(xmlfile):
    allegroProducts = list()

    tree = eT.parse(xmlfile)
    root = tree.getroot()

    products = root.find('ng:PRODUKTY', ns)

    for prod in products:
        state = prod.find('ng:STAN', ns)
        count = state.text
        if int(count) < 5:
            continue

        price = prod.find('ng:CENA_BRUTTO', ns)
        if price.text is None:
            continue

        # Mój narzut
        price.text = str(float(price.text) * 0.92)

        try:
            allegroProducts += AllegroTire(prod)
        except (LookupError, ValueError) as e:
            log.debug(repr(e))
            continue

    return allegroProducts


if __name__ == '__main__':
    from main import getCategoryParams

    createAllegroProducts('/home/daniel/Documents/1_praca/1_Freelance/1_handel/1_allegro/1_sklepy/LuckyStar/sklep.xml')
