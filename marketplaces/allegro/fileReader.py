import pickle


def saveObjToFile(obj, file):
    with open(file, 'wb') as f:
        pickle.dump(obj, f)


def readObjFromFile(file):
    with open(file, 'rb') as f:
        return pickle.load(f)
