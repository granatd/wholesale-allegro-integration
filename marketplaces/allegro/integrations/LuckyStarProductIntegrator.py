import os
import re
import traceback
import logging as log

fmt = "[%(levelname)s:%(filename)s:%(lineno)s: %(funcName)s()] %(message)s"
log.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"), format=fmt)
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
        'Sezon': 'Identyfikator',
        'Waga (z opakowaniem)': 'Waga',
        # 'Bieżnik': 'Głębokość bieżnika [mm]',
        # 'Przeznaczenie': 'Typ', # np. terenowe, zimowe, autobus
        # 'Rodzaj': 'Opis -> bezdętkowa',  # np. bez/dętkowe
        #  'Oś': None, # np. prowadząca, napędowa, naczepowa, uniwersalna
        #  'Liczba płócien (PR)': 'Opis-> warstwowa',
        # 'Konstrukcja': 'Opis/Informacje ogólne/Przeznaczenie/Techniczne cechy opony -> radialna, diagonalna',
        'Typ motocykla': None,
        'Informacje dodatkowe': None,
    }

    description = {"sections": [
            {  # Section 1
                "items": [{
                    "type": "TEXT",
                    "content": '',
                }]
            }, {  # Section 2
                "items": [{
                    "type": "TEXT",
                    "content": '',
                }, {
                    "type": "IMAGE",
                    "url": None,
                }]
            }, {  # Section 3
                "items": [{
                    "type": "TEXT",
                    "content": '',
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
        ]}

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
        self.stockCount = self.prod.getStockCount()
        return self.stockCount

    def getCategory(self):
        season = None
        prodType = None
        self.category = None

        try:
            prodType = self.prod.getType().lower()
            season = self.prod.getSeason().lower()
        except LookupError as e:
            if str(e).lower() == 'typ':
                raise LookupError('Category not found!')

        if prodType == 'samochody osobowe':
            if season is None:
                self.category = '257689'
            elif season == 'letnie':
                self.category = '257689'
            elif season == 'całoroczne':
                self.category = '257692'
        elif prodType == 'samochody terenowe, SUV, Pickup':
            if season is None:
                self.category = '257694'
            elif season == 'letnie':
                self.category = '257694'
            elif season == 'całoroczne':
                self.category = '257696'
        elif prodType == 'samochody dostawcze':
            if season is None:
                self.category = '257698'
            elif season == 'letnie':
                self.category = '257698'
            elif season == 'całoroczne':
                self.category = '257700'
        elif prodType == 'przemysłowe':
            if season is None:
                self.category = None
            elif season == 'letnie':
                self.category = None
            elif season == 'całoroczne':
                self.category = None

        if self.category is None:
            raise ValueError('Unrecognized category!')

        return self.category

    def getParams(self, availParams):
        params = list()
        availableParams = availParams['parameters']

        for availParam in availableParams:
            try:
                if availParam['name'].lower() == 'stan' or \
                        availParam['name'].lower() == 'liczba opon w ofercie':
                    params.append({
                        'id': availParam['id'],
                        'valuesIds': [
                            availParam['dictionary'][0]['id'],
                        ],
                        'values': [],
                        'rangeValue': None
                    })
                else:
                    val = self.prod.getDescValue(self.allegro2ngMap[availParam['name']])

                    if availParam['type'].lower() == 'dictionary':
                        valueIds = list()
                        availParamValues = availParam['dictionary']

                        for item in availParamValues:
                            availVal = item['value']

                            pattern = r'\b{}\b'.format(val.lower())
                            if re.search(pattern, availVal.lower()):
                                valueIds.append(item['id'])
                                if availParam['restrictions']['multipleChoices'] is False:
                                    break
                        if not valueIds and availParam['options']['ambiguousValueId'] is not None:
                            valueIds.append(availParam['options']['ambiguousValueId'])
                        if availParam['required'] is True and not valueIds:
                            valueIds.append(availParam['dictionary'][-1]['id'])

                        params.append({
                            'id': availParam['id'],
                            'valuesIds': valueIds,
                            'values': [],
                            'rangeValue': None
                        })

                    elif (availParam['type'].lower() == 'float' or
                          availParam['type'].lower() == 'integer') and \
                            availParam['restrictions']['range'] is False:
                        val = float(val)
                        if val < availParam['restrictions']['min']:
                            val = availParam['restrictions']['min']
                        elif val > availParam['restrictions']['max']:
                            val = availParam['restrictions']['max']

                        params.append({
                            'id': availParam['id'],
                            'valuesIds': [],
                            'values': val,
                            'rangeValue': None
                        })
                    elif availParam['type'].lower() is 'string':
                        params.append({
                            'id': availParam['id'],
                            'valuesIds': [],
                            'values': val,
                            'rangeValue': None
                        })
            except LookupError as e:
                log.debug('\'{}\' {}'.format(availParam['name'], repr(e)))
                # print('\n[Backtrace from getting \'{}\' parameter:]'.format(param['name']))
                # traceback.print_tb(e.__traceback__)
                continue

        self.params = {'parameters': params}
        return self.params

    def getDesc(self):
        section1 = self.description['sections'][0]
        item1 = section1['items'][0]
        item1['content'] += '<p><b>Pełna nazwa:</b> {}</p>\n'.format(self.prod.getTitle())

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
            item1['content'] += '<p><b>Typ:</b> {}</p>\n'.format(self.prod.getType())
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

        if len(self.images) > 0:
            item2 = section2['items'][1]
            item2['url'] = self.images[0]

        section3 = self.description['sections'][2]
        item1 = section3['items'][0]

        try:
            item1['content'] += '<p><b>Informacje ogólne:</b>\n{}</p>\n'.format(self.prod.getOverallInfo())
        except LookupError as e:
            log.debug(repr(e))

        if len(self.images) > 1:
            section4 = self.description['sections'][3]
            item1 = section4['items'][0]
            item1['url'] = self.images[1]

        if len(self.images) > 2:
            item2 = section2['items'][1]
            item2['url'] = self.images[2]

        return self.description
