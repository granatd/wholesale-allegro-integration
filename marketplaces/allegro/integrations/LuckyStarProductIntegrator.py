import os
import logging as log

log.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))
log = log.getLogger(__name__)


class LuckyStarProductIntegrator:

    def __init__(self, prod):
        self.prod = prod

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
        # 'Bieżnik': 'Głębokość bieżnika [mm]',
        # 'Przeznaczenie': 'Typ', # np. terenowe, zimowe, autobus
        # 'Rodzaj': 'Opis -> bezdętkowa',  # np. bez/dętkowe
        #  'Oś': None, # np. prowadząca, napędowa, naczepowa, uniwersalna
        #  'Liczba płócien (PR)': 'Opis-> warstwowa',
        # 'Konstrukcja': 'Opis/Informacje ogólne/Przeznaczenie/Techniczne cechy opony -> radialna, diagonalna',
        'Typ motocykla': None,
        'informacje dodatkowe': None,
    }

    description = {"sections": [
            {  # Section 1
                "items": [{
                    "type": "TEXT",
                    "content": None,
                }]
            }, {  # Section 2
                "items": [{
                    "type": "TEXT",
                    "content": None,
                }, {
                    "type": "IMAGE",
                    "url": None,
                }]
            }, {  # Section 3
                "items": [{
                    "type": "TEXT",
                    "content": None,
                }]
            }, {  # Section 4
                "items": [{
                    "type": "IMAGE",
                    "url": None,
                }, {
                    "type": "IMAGE",
                    "url": None,
                }]
            }
        ]},

    prod = None
    title = None
    category = None
    params = None
    stockCount = None
    images = list()

    def getTitle(self):
        self.title = self.prod.getTitle()
        return self.title

    def getImages(self):
        self.images = self.prod.getImages()
        return self.images

    def getStockCount(self):
        self.stockCount = self.prod.getStockCount
        return self.stockCount

    def getCategory(self):
        self.category = None

        if self.prod.getType() == 'samochody osobowe':
            if self.prod.getSeason() is None:
                self.category = '257689'
            elif self.prod.getSeason() == 'letnie':
                self.category = '257689'
            elif self.prod.getSeason() == 'całoroczne':
                self.category = '257692'
        elif self.prod.getType() == 'samochody terenowe, SUV, Pickup':
            if self.prod.getSeason() is None:
                self.category = '257694'
            elif self.prod.getSeason() == 'letnie':
                self.category = '257694'
            elif self.prod.getSeason() == 'całoroczne':
                self.category = '257696'
        elif self.prod.getType() == 'samochody dostawcze':
            if self.prod.getSeason() is None:
                self.category = '257698'
            elif self.prod.getSeason() == 'letnie':
                self.category = '257698'
            elif self.prod.getSeason() == 'całoroczne':
                self.category = '257700'
        elif self.prod.getType() == 'przemysłowe':
            if self.prod.getSeason() is None:
                self.category = None
            elif self.prod.getSeason() == 'letnie':
                self.category = None
            elif self.prod.getSeason() == 'całoroczne':
                self.category = None

        if self.category is None:
            raise ValueError('Value not found!')

        return self.category

    def getParams(self, availParams):
        params = list()
        availableParams = availParams['parameters']

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
                    val = float(self.prod.getDescValue(self.allegro2ngMap[param['name']]))
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
                        'values': self.prod.getDescValue(self.allegro2ngMap[param['name']]),
                        'rangeValue': None
                    }
            except LookupError as e:
                log.debug(repr(e))
                continue

        self.params = {'parameters': params}
        return self.params

    def getDesc(self):
        section1 = self.description['sections'][0]
        item1 = section1['items'][0]
        item1['content'] = '<p><b>Pełna nazwa:</b> {}</p>\n'.format(self.prod.getTitle())

        try:
            item1['content'] += '<p><b>Producent:</b> {}</p>\n'.format(self.prod.getProducer())
        except LookupError as e:
            log.debug(repr(e))

        try:
            item1['content'] += '<p><b>Model:</b> {}</p>\n'.format(self.prod.getModel())
        except LookupError as e:
            log.debug(repr(e))

        section2 = self.description['sections'][1]
        item1 = section2['items'][0]

        try:
            item1['content'] += '<p><b>Opory toczenia:</b> {}</p>\n'.format(self.prod.getRotationResistance())
        except LookupError as e:
            log.debug(repr(e))

        try:
            item1['content'] += '<p><b>Hamowanie na mokrym:</b> {}</p>\n'.format(self.prod.getWetTraction())
        except LookupError as e:
            log.debug(repr(e))

        try:
            item1['content'] += '<p><b>Poziom hałasu:</b> {}</p>\n'.format(self.prod.getNoiseLevel())
        except LookupError as e:
            log.debug(repr(e))

        try:
            item1['content'] = '<p><b>Typ:</b> {}</p>\n'.format(self.prod.getType())
        except LookupError as e:
            log.debug(repr(e))

        try:
            item1['content'] += '<p><b>Sezon:</b> {}</p>\n'.format(self.prod.getSeason())
        except LookupError as e:
            log.debug(repr(e))

        try:
            item1['content'] += '<p><b>Rozmiar:</b> {}</p>\n'.format(self.prod.getSize())
        except LookupError as e:
            log.debug(repr(e))

        try:
            item1['content'] += '<p><b>Szerokość:</b> {}</p>\n'.format(self.prod.getWidth())
        except LookupError as e:
            log.debug(repr(e))

        try:
            item1['content'] += '<p><b>Wysokość:</b> {}</p>\n'.format(self.prod.getHeight())
        except LookupError as e:
            log.debug(repr(e))

        try:
            item1['content'] += '<p><b>Rozmiar felgi:</b> {}</p>\n'.format(self.prod.getRimSize())
        except LookupError as e:
            log.debug(repr(e))

        try:
            item1['content'] += '<p><b>Indeks prędkości:</b> {}</p>\n'.format(self.prod.getVmax())
        except LookupError as e:
            log.debug(repr(e))

        try:
            item1['content'] += '<p><b>Indeks nośności:</b> {}</p>\n'.format(self.prod.getLoadIndex())
        except LookupError as e:
            log.debug(repr(e))

        try:
            item1['content'] += '<p><b>Kod producenta:</b> {}</p>\n'.format(self.prod.getProducerCode())
        except LookupError as e:
            log.debug(repr(e))

        try:
            item1['content'] += '<p><b>EAN:</b> {}</p>\n'.format(self.prod.getEAN())
        except LookupError as e:
            log.debug(repr(e))

        try:
            item1['content'] += '<p><b>Identyfikator:</b> {}</p>\n'.format(self.prod.getDestination())
        except LookupError as e:
            log.debug(repr(e))

        try:
            item1['content'] += '<p><b>Waga:</b> {}</p>\n'.format(self.prod.getWeight())
        except LookupError as e:
            log.debug(repr(e))

        try:
            item1['content'] += '<p><b>Objętość:</b> {}</p>\n'.format(self.prod.getVolumeSize())
        except LookupError as e:
            log.debug(repr(e))

        item2 = section2['items'][1]
        item2['url'] = self.images[0]

        section3 = self.description['sections'][2]
        item1 = section3['items'][0]

        try:
            item1['content'] = '<p><b>Informacje ogólne:</b>\n{}</p>\n'.format(self.prod.getOverallInfo())
        except LookupError as e:
            log.debug(repr(e))

        section4 = self.description['sections'][3]
        item1 = section4['items'][0]
        item1['url'] = self.images[1]

        item2 = section2['items'][1]
        item2['url'] = self.images[2]

        return self.description
