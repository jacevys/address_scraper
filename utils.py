import json
import os
import numpy as np
import requests
import time
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
def get_oklink_label(chain_name: str, address: str):
    url = f"https://www.oklink.com/api/v5/explorer/address/entity-label?chainShortName={chain_name}&address={address}"

    payload = ""
    headers = {
    'Ok-Access-Key': 'eedb6f15-f0d3-47e6-a990-6647ef636bb7'
    }

    response = requests.request("GET", url, headers=headers, data=payload).json()

    return response
#
def func_1():
    data_list = readJson(path='./label_database/tron.json')
    counter = 0
    total_counter = 0

    for address in data_list.keys():
        if data_list[address]['misttrack_label_type'] == 'defi':
            response = get_oklink_label(chain_name='tron', address=address)

            if len(response['data']) > 0:
                counter += 1

            total_counter += 1
            time.sleep(1)

            print(data_list[address])
            print('\n')
            print(response)
            print(f'counter: {counter}/{total_counter}')
            print('-' * 50)
#
if __name__ == '__main__':
    response = get_misttrack_label(coin='ETH', address='0x7a250d5630b4cf539739df2c5dacb4c659f2488d')
    print(response)
#
'''
labeld: 413/2656
'''