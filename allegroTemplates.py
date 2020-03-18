
class Auction:
    template = {
         'additionalServices': None,
         'afterSalesServices': {'impliedWarranty': {'id': '95b451bf-7fd6-4d46-9bc1-ac6516eeb065'},
                                'returnPolicy': {'id': 'f7b5005b-4b46-45d7-bab8-e17208729f2c'},
                                'warranty': {'id': '593b3ed0-655c-40e6-acbc-7782351cca75'}},
         'attachments': None,
         'category': None,          # to fill
         'compatibilityList': None,
         'contact': None,
         'delivery': {'additionalInfo': None,
                      'handlingTime': 'PT24H',  # to customize
                      'shipmentDate': None,
                      'shippingRates': {'id': 'cde2d24a-ab38-461d-96da-ade36d99e7cf'}},
         'description': {"sections": [
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
         'ean': None,
         'images': None,
         'location': {'city': 'Łódź',
                      'countryCode': 'PL',
                      'postCode': '90-619',
                      'province': 'LODZKIE'},
         'name': None,
         'parameters': None,
         'payments': {'invoice': 'VAT'},
         'product': None,
         'publication': {'duration': None,
                         'endedBy': None,
                         'endingAt': None,
                         'republish': True,
                         'startingAt': None,
                         'status': 'ACTIVE'},
         'sellingMode': {'format': 'BUY_NOW',
                         'minimalPrice': None,
                         'price': {'amount': '609', 'currency': 'PLN'},
                         'startingPrice': None},
         'sizeTable': None,
         'stock': {'available': 2, 'unit': 'UNIT'},
    }

    def setTitle(self, name):
        self.template['name'] = name

    def setImages(self, images):
        self.template['images'] = images

    def setCategory(self, category):
        self.template['category'] = str(category)

    def setDescription(self, desc):
        self.template['description'] = desc

    def setParams(self, params):
        self.template['parameters'] = params

    def setStockCount(self, count):
        self.template['stock'] = str(count)

    def __init__(self, name, category, images, desc, params, count):
        self.setTitle(name)
        self.setCategory(category)
        self.setImages(images)
        self.setDescription(desc)
        self.setParams(params)
        self.setStockCount(count)

