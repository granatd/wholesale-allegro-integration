import os
import re
import html
import logging as log

WHEELS_COUNT = 4

fmt = "[%(levelname)s:%(filename)s:%(lineno)s: %(funcName)s()] %(message)s"
log.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"), format=fmt)
log = log.getLogger(__name__)


class LuckyStarProductIntegrator:

    def __init__(self, prod):
        self.prod = prod

        self.allegro2ngMap = {
            'Marka': 'Producent',
            'Model': 'Nazwa',
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

        self.description = {"sections": [
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
                    "url": '',
                }]
                # }, {  # Section 3
                #     "items": [{
                #         "type": "TEXT",
                #         "content": '',
                #     }]
                # }, {  # Section N
                #     "items": [{
                #         "type": "IMAGE",
                #         "url": '',
                #     }, {
                #         "type": "TEXT",
                #         "content": '',
                #     }]
                # }, {  # Section N+1
                #     "items": [{
                #         "type": "TEXT",
                #         "url": '',
                #     }, {
                #         "type": "IMAGE",
                #         "content": '',
                #     }],
                # }, {  # Last Section
                #     "items": [{
                #         "type": "TEXT",
                #         "url": '',
                #     }],
            }
        ]}

        self.title = None
        self.EAN = None
        self.price = None
        self.category = None
        self.params = None
        self.stockCount = None
        self.images = list()
        self.availParam = None
        self._descriptionSet = False

    def getTitle(self):
        prefix = ''
        cat = {'id': ''}

        try:
            cat = self.getCategory()
        except (ValueError, LookupError):
            pass

        if WHEELS_COUNT > 1 and not cat['id'] == '301094':  # motorbikes
            prefix = str(WHEELS_COUNT) + 'x '

        if self.title is None:
            self.title = prefix + self.prod.getTitle()

        return self.title[0:45]

    def getEAN(self):
        if self.EAN is None:
            self.EAN = self.prod.getEAN()

        return html.escape(self.EAN)

    def getPrice(self):
        if self.price is not None:
            return self.price

        price = "{:.2f}".format(float(self.prod.getPrice()) * WHEELS_COUNT)
        self.price = {'amount': price, 'currency': 'PLN'}

        return self.price

    def getImages(self):
        if not self.images:
            self.images = self.prod.getImages()

        return self.images

    def getStockCount(self):
        if self.stockCount is not None:
            return self.stockCount

        stockCount = int(self.prod.getStockCount())/WHEELS_COUNT

        self.stockCount = {'available': stockCount, 'unit': 'UNIT'}

        return self.stockCount

    def getCategory(self):
        season = None
        prodType = None

        if self.category is not None:
            return self.category

        try:
            prodType = self.prod.getType().lower()
            season = self.prod.getSeason().lower()
        except LookupError as e:
            if str(e).lower() == 'typ':
                raise LookupError('Category not found for product \'{}\'!'.format(self.prod.getTitle()))

        if prodType == 'samochody osobowe':
            if season is None:
                self.category = {'id': '257689'}
            elif season == 'letnie':
                self.category = {'id': '257689'}
            elif season == 'całoroczne':
                self.category = {'id': '257692'}
        elif prodType == 'samochody terenowe, SUV, Pickup':
            if season is None:
                self.category = {'id': '257694'}
            elif season == 'letnie':
                self.category = {'id': '257694'}
            elif season == 'całoroczne':
                self.category = {'id': '257696'}
        elif prodType == 'samochody dostawcze':
            if season is None:
                self.category = {'id': '257698'}
            elif season == 'letnie':
                self.category = {'id': '257698'}
            elif season == 'całoroczne':
                self.category = {'id': '257700'}
        elif prodType == 'przemysłowe':
            if season is None:
                self.category = {'id': '257689'}  # lub '257707' - do innych pojazdów
            elif season == 'letnie':
                self.category = {'id': '257689'}
            elif season == 'całoroczne':
                self.category = {'id': '257692'}
        elif prodType == 'quady':
            self.category = {'id': '257706'}
        elif prodType == 'motocykle i skutery':
            self.category = {'id': '301094'}

        if self.category is None:
            raise ValueError('Unrecognized category!')

        return self.category

    def isFirstListParam(self):
        return self.availParam['name'].lower() == 'stan'

    def appendFirstListParam(self, params):
        params.append({
            'id': self.availParam['id'],
            'valuesIds': [
                self.availParam['dictionary'][0]['id'],
            ],
            'values': [],
            'rangeValue': None
        })

    def isWheelsCountParam(self):
        return self.availParam['name'].lower() == 'liczba opon w ofercie'

    def appendWheelsParam(self, params):
        wheels = WHEELS_COUNT
        assert(wheels > 0)

        params.append({
            'id': self.availParam['id'],
            'valuesIds': [
                self.availParam['dictionary'][wheels - 1]['id'],
            ],
            'values': [],
            'rangeValue': None
        })

    def trySetDefaultParam(self, params):
        valueIds = list()

        if self.availParam['type'].lower() == 'dictionary':
            if self.availParam['options']['ambiguousValueId'] is not None:
                valueIds.append(self.availParam['options']['ambiguousValueId'])
            if self.availParam['required'] is True and not valueIds:
                valueIds.append(self.availParam['dictionary'][-1]['id'])

            if valueIds:
                params.append({
                    'id': self.availParam['id'],
                    'valuesIds': valueIds,
                    'values': [],
                    'rangeValue': None
                })
                return True

        return False

    def appendParam(self, params):
        if self.isWheelsCountParam():
            val = str(WHEELS_COUNT)
        else:
            val = self.prod.getDescValue(self.allegro2ngMap[self.availParam['name']])

        if self.availParam['type'].lower() == 'dictionary':
            valueIds = list()
            availParamValues = self.availParam['dictionary']

            for item in availParamValues:
                availVal = item['value']

                pattern = r'\b{}\b'.format(val.lower())  # TODO fix this
                if re.search(pattern, availVal.replace('/', ''), re.IGNORECASE):
                    valueIds.append(item['id'])
                    if self.availParam['restrictions']['multipleChoices'] is False:
                        break

            if not valueIds:
                raise LookupError

            params.append({
                'id': self.availParam['id'],
                'valuesIds': valueIds,
                'values': [],
                'rangeValue': None
            })

        elif (self.availParam['type'].lower() == 'float' or
              self.availParam['type'].lower() == 'integer') and \
                self.availParam['restrictions']['range'] is False:
            val = float(val.replace(',', '.'))
            if not val % 1:
                val = int(val)

            if val < self.availParam['restrictions']['min']:
                val = self.availParam['restrictions']['min']
            elif val > self.availParam['restrictions']['max']:
                val = self.availParam['restrictions']['max']

            params.append({
                'id': self.availParam['id'],
                'valuesIds': [],
                'values': [val],
                'rangeValue': None
            })
        elif self.availParam['type'].lower() == 'string':
            params.append({
                'id': self.availParam['id'],
                'valuesIds': [],
                'values': [val],
                'rangeValue': None
            })

    def getParams(self, availParams):

        if self.params is not None:
            return self.params

        params = list()
        availableParams = availParams['parameters']

        for self.availParam in availableParams:
            try:
                if self.isFirstListParam():
                    self.appendFirstListParam(params)
                else:
                    self.appendParam(params)
            except LookupError as e:
                if not self.trySetDefaultParam(params):
                    log.debug('\'{}\' {}'.format(self.availParam['name'], repr(e)))
                # print('\n[Backtrace from getting \'{}\' parameter:]'.format(param['name']))
                # traceback.print_tb(e.__traceback__)
                continue

        self.params = params
        return self.params

    def isDescriptionSet(self):
        return self._descriptionSet

    def getDesc(self, allegroImgLinks):

        if self.isDescriptionSet():
            return self.description

        if allegroImgLinks is None:
            allegroImgLinks = list()

        # ==================================== SECTION 1 ===========================================
        section1 = self.description['sections'][0]

        # ====== ITEM 1 ======
        item = section1['items'][0]
        item['content'] += '<p><b>Pełna nazwa:</b> {}</p>\n'.format(self.getTitle())

        try:
            item['content'] += '<p><b>Producent:</b> {}</p>\n'.format(html.escape(self.prod.getProducer()))
        except LookupError as e:
            log.debug(repr(e))

        try:
            item['content'] += '<p><b>Model:</b> {}</p>\n'.format(html.escape(self.prod.getModel()))
        except LookupError as e:
            log.debug(repr(e))

        if not item['content']:
            raise LookupError('Description is empty!')

        # ==================================== SECTION 2 ===========================================
        section2 = self.description['sections'][1]

        # ====== ITEM 1 ======
        item = section2['items'][0]

        try:
            item['content'] += '<p><b>Opory toczenia:</b> {}</p>\n'.format(html.escape(self.prod.getRotationResistance()))
        except LookupError as e:
            log.debug(repr(e))

        try:
            item['content'] += '<p><b>Hamowanie na mokrym:</b> {}</p>\n'.format(html.escape(self.prod.getWetTraction()))
        except LookupError as e:
            log.debug(repr(e))

        try:
            item['content'] += '<p><b>Poziom hałasu:</b> {}</p>\n'.format(html.escape(self.prod.getNoiseLevel()))
        except LookupError as e:
            log.debug(repr(e))

        try:
            item['content'] += '<p><b>Typ:</b> {}</p>\n'.format(html.escape(self.prod.getType()))
        except LookupError as e:
            log.debug(repr(e))

        try:
            item['content'] += '<p><b>Sezon:</b> {}</p>\n'.format(html.escape(self.prod.getSeason()))
        except LookupError as e:
            log.debug(repr(e))

        try:
            item['content'] += '<p><b>Rozmiar:</b> {}</p>\n'.format(html.escape(self.prod.getSize()))
        except LookupError as e:
            log.debug(repr(e))

        try:
            item['content'] += '<p><b>Szerokość:</b> {}</p>\n'.format(html.escape(self.prod.getWidth()))
        except LookupError as e:
            log.debug(repr(e))

        try:
            item['content'] += '<p><b>Wysokość:</b> {}</p>\n'.format(html.escape(self.prod.getHeight()))
        except LookupError as e:
            log.debug(repr(e))

        try:
            item['content'] += '<p><b>Rozmiar felgi:</b> {}</p>\n'.format(html.escape(self.prod.getRimSize()))
        except LookupError as e:
            log.debug(repr(e))

        try:
            item['content'] += '<p><b>Indeks prędkości:</b> {}</p>\n'.format(html.escape(self.prod.getVmax()))
        except LookupError as e:
            log.debug(repr(e))

        try:
            item['content'] += '<p><b>Indeks nośności:</b> {}</p>\n'.format(html.escape(self.prod.getLoadIndex()))
        except LookupError as e:
            log.debug(repr(e))

        try:
            item['content'] += '<p><b>Kod producenta:</b> {}</p>\n'.format(html.escape(self.prod.getProducerCode()))
        except LookupError as e:
            log.debug(repr(e))

        try:
            item['content'] += '<p><b>EAN:</b> {}</p>\n'.format(html.escape(self.getEAN()))
        except LookupError as e:
            log.debug(repr(e))

        try:
            item['content'] += '<p><b>Identyfikator:</b> {}</p>\n'.format(html.escape(self.prod.getDestination()))
        except LookupError as e:
            log.debug(repr(e))

        try:
            item['content'] += '<p><b>Waga:</b> {}</p>\n'.format(html.escape(self.prod.getWeight()))
        except LookupError as e:
            log.debug(repr(e))

        try:
            item['content'] += '<p><b>Objętość:</b> {}</p>\n'.format(html.escape(self.prod.getVolumeSize()))
        except LookupError as e:
            log.debug(repr(e))

        if not item['content']:
            del section2['items'][0]

        # ====== ITEM 2 =======
        item = section2['items'][1]
        try:
            item['url'] = allegroImgLinks[0]['url']
        except IndexError:
            log.debug('Can\'t make img item in section2!')
            del section2['items'][1]

        if not section2['items']:
            raise LookupError('Description is incomplete!')

        # ==================================== SECTION 3 ===========================================
        section3 = {
            "items": [],
        }

        # ====== ITEM 1 ======
        item = dict()

        try:
            item['content'] = '<p><b>Informacje ogólne:</b></p>\n' \
                              '<p>{}</p>\n'.format(html.escape(self.prod.getOverallInfo()))
            item['type'] = 'TEXT'
        except LookupError as e:
            log.debug(repr(e))

        if item:
            section3['items'].append(item)

        if section3['items']:
            self.description['sections'].append(section3)

        # ==================================== SECTIONS N AND N+1 ========================================
        maxAdditionalSections = 7
        additionalDescriptions = self.prod.getAdditionalDescription()

        def makeImgItem(additionalDescNum):
            item = dict()

            try:
                item['url'] = allegroImgLinks[1 + additionalDescNum]['url']
                item['type'] = 'IMAGE'
            except IndexError:
                log.debug('Can\'t make img item in sectionN!')

            return item

        def makeTextItem(additionalDescriptions):
            item = dict()

            try:
                additionalDescName, additionalDescVal = additionalDescriptions.pop()

                additionalDescName = html.escape(additionalDescName)
                additionalDescVal = html.escape(additionalDescVal)

                item['content'] = '<p><b>{}:</b></p>\n' \
                                  '<p>{}</p>\n'.format(additionalDescName, additionalDescVal)
                item['type'] = 'TEXT'
            except IndexError:
                log.debug('Can\'t make text item in sectionN!')

            return item

        def makeAdditionalSection(N):
            if int(N) % 2 == 1:
                item1Type = 'TEXT'
            else:
                item1Type = 'IMAGE'

            sectionN = {
                "items": []
            }
            items = sectionN['items']

            imgItem = makeImgItem(N)
            textItem = makeTextItem(additionalDescriptions)

            if not imgItem and not textItem:
                return dict()

            if item1Type == 'TEXT':
                if textItem:
                    items.append(textItem)
                if imgItem:
                    items.append(imgItem)
            else:
                if imgItem:
                    items.append(imgItem)
                if textItem:
                    items.append(textItem)

            return sectionN

        for N in range(maxAdditionalSections):
            sectionN = makeAdditionalSection(N)

            if sectionN:
                self.description['sections'].append(sectionN)
            else:
                break

        # ==================================== LAST SECTION ===========================================
        sectionLast = {
            "items": [],
        }

        # ====== ITEM 1 ======
        item = dict()

        try:
            item['content'] = '<p><b>Pasuje do:</b>\n{}</p>\n'.format(html.escape(self.prod.getCompatibleModelsDesc()))
            item['type'] = 'TEXT'
        except LookupError as e:
            log.debug(repr(e))

        if item:
            sectionLast['items'].append(item)

        if sectionLast['items']:
            self.description['sections'].append(sectionLast)

        # =============================================================================================

        self._descriptionSet = True
        return self.description
