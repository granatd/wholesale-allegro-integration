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

    prod = None
    title = None
    category = None
    images = None
    desc = None
    params = None
    stockCount = None

    def getTitle(self):
        return self.prod.getTitle()

    def getImages(self):
        return self.prod.getImages()

    def getStockCount(self):
        return self.prod.getStockCount

    def getCategory(self):
        if self.prod.getType() == 'samochody osobowe':
            if self.prod.getSeason() is None:
                return '257689'
            elif self.prod.getSeason() == 'letnie':
                return '257689'
            elif self.prod.getSeason() == 'całoroczne':
                return '257692'
        elif self.prod.getType() == 'samochody terenowe, SUV, Pickup':
            if self.prod.getSeason() is None:
                return '257694'
            elif self.prod.getSeason() == 'letnie':
                return '257694'
            elif self.prod.getSeason() == 'całoroczne':
                return '257696'
        elif self.prod.getType() == 'samochody dostawcze':
            if self.prod.getSeason() is None:
                return '257698'
            elif self.prod.getSeason() == 'letnie':
                return '257698'
            elif self.prod.getSeason() == 'całoroczne':
                return '257700'
        elif self.prod.getType() == 'przemysłowe':
            if self.prod.getSeason() is None:
                return None
            elif self.prod.getSeason() == 'letnie':
                return None
            elif self.prod.getSeason() == 'całoroczne':
                return None

        raise ValueError('Value not found!')

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
                    val = float(self.prod.getValue(self.allegro2ngMap[param['name']]))
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
                        'values': self.prod.getValue(self.allegro2ngMap[param['name']]),
                        'rangeValue': None
                    }
            except LookupError as e:
                log.debug(repr(e))
                continue

        return {'parameters': params}

    def getDesc(self):
        pass

