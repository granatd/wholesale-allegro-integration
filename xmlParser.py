import requests
import xml.etree.ElementTree as eT


ns = {'ng': 'http://nowegumy.pl'}


def saveXML():

    url = 'https://xml.nowegumy.pl/38c07d9eb6f585cb2e363aa8d83443b1b9fcc722/sklep.xml'
    resp = requests.get(url)

    with open('sklep.xml', 'wb') as f:
        f.write(resp.content)


def createAllegroProduct(ngProd):
    pass


def parseXML(xmlfile):
    global allegroProducts
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

        # narzut
        price.text = str(float(price.text) * 0.92)

        createAllegroProduct(prod)
        allegroProducts.append(prod)


if __name__ == '__main__':
    parseXML('/home/daniel/Documents/1_praca/1_Freelance/1_handel/1_allegro/1_sklepy/LuckyStar/sklep.xml')
