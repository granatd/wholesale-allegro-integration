import os
import pickle
import pathlib


def saveObjToFile(obj, file):
    directory = os.path.dirname(file)
    if not os.path.isdir(directory):
        pathlib.Path(directory).mkdir(parents=True, exist_ok=True)

    with open(file, 'wb') as f:
        pickle.dump(obj, f)


def readObjFromFile(file):
    with open(file, 'rb') as f:
        return pickle.load(f)
