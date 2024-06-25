import json
import os
import numpy as np
import requests
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
def get_misttrack_label(coin: str, address: str) -> None:
    mapping = {'BTC': 'BTC', 'ETH': 'ETH', 'TRON': 'TRX'}
    api_key_mt = 'd8ab0f7a43cc49618af572fa6c5e1c0c'
    url = ('https://openapi.misttrack.io/v1/address_labels?coin={}&address={}&api_key={}'
           .format(mapping[coin], address, api_key_mt))

    response = requests.get(url=url).json()

    return response
#
if __name__ == '__main__':
    response = get_misttrack_label(coin='BTC', address='3JEk9g87E9CEnxNWk1foxyVW27YEAmqaWQ')
    print(response)
#