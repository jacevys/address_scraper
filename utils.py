import json
import os
import numpy as np
#
def readJson(path: str):
    with open(path, 'r', encoding='utf-8-sig') as json_file:
        buffer = json.load(json_file)
    
    return buffer
#
def saveJson(save_path, wallet_list):
    with open(save_path, 'w') as json_file:
        json.dump(wallet_list, json_file, indent=2)

    print('saved')
#
def func_1(split_ratio, version):
    data_lists = ['others', 'exchange', 'kyc', 'scam']
    train_set = {}
    test_set = {}
    duplicate = []

    for data_list in data_lists:
        dataset = readJson(f'./data/{data_list}_jace.json')
        index = int(len(dataset.keys()) * split_ratio)

        for i, key in enumerate(dataset.keys()):
            feature = dataset[key]

            feature['Label'] = data_list

            if key in train_set.keys() or key in test_set.keys():
                duplicate.append(key)
            if i < index:
                train_set[key] = feature
            else:
                test_set[key] = feature

    for key in duplicate:
        try:
            del train_set[key]
        except:
            pass
        try:
            del test_set[key]
        except:
            pass
    
    for key in duplicate:
        if key in train_set.keys() or key in test_set.keys():
            print('attention')

    print(len(train_set.keys()))
    print(len(test_set.keys()))
    print(len(duplicate))

    saveJson(save_path=f'./data/train_set_{version}.json', wallet_list=train_set)
    saveJson(save_path=f'./data/test_set_{version}.json', wallet_list=test_set)
#
if __name__ == '__main__':
    func_1(split_ratio=0.8, version=1)
#