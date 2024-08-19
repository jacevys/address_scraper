import json
import os
import numpy as np
import requests

#
def readJson(path: str):
    if not os.path.exists(path):
        return {}
    
    if os.path.getsize(path) == 0:
        print(f"File is empty: {path}")
        return {}

    with open(path, 'r', encoding='utf-8-sig') as json_file:
        buffer = json.load(json_file)
    
    return buffer
#
def write_json(json_file_path, data, address):
    file_exists = os.path.exists(json_file_path)
    buffer = {}

    if not file_exists:
        with open(json_file_path, 'w') as json_file:
            json.dump(data, json_file, indent=2)
    else:
        with open(json_file_path, 'r') as json_file:
            existing_data = json.load(json_file)

        if address in existing_data.keys():
            existing_feature = existing_data[address]
        else:
            existing_feature = {}

        for key in data[address]:
            existing_feature[key] = data[address][key]

        buffer[address] = existing_feature
        existing_data.update(buffer)

        with open(json_file_path, 'w') as json_file:
            json.dump(existing_data, json_file, indent=2)

    # print('數據已寫入json')
#
def remove_keys_from_json(json_file_path: str, keys: list[str]) -> None:
    with open(json_file_path, 'r') as json_file:
        data = json.load(json_file)
    
    for key in keys:
        data.pop(key, None)
    
    with open(json_file_path, 'w') as json_file:
        json.dump(data, json_file, indent=2)
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
    response = get_misttrack_label(coin='BTC', address='19iqYbeATe4RxghQZJnYVFU4mjUUu76EA6')
    print(response)
#