import requests
import get_tronscan_feature
import time
import numpy as np
from typing import *
import json
import os
#
def dfs(start_address: str, visited: set, element_list: List,\
        max_element: int, headers: str, params: dict,\
        pages: int):

    params['address'] = start_address

    visited.add(start_address)

    dfs_total_trx = get_tronscan_feature.get_trx_from_tronscan(headers, params, pages)
    total_trx_simplfied = func_1(address=start_address, total_trx=dfs_total_trx)

    for trx in total_trx_simplfied:
        if trx[0] not in visited:

            if trx[0] == 'TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t':
                continue

            balance_now = get_time_and_balance(address=trx[0])[1]
            trx.append(balance_now)

            ai_label = get_ai_label(address=trx[0])

            if type(ai_label) == str or ai_label == None:
                continue

            if list(ai_label.keys())[0] == 'exchange' or list(ai_label.keys())[0] == 'kyc':
                buffer = {}

                buffer[trx[0]] = {
                    'receive_send': trx[1],
                    'trx_value': trx[2],
                    'balance': trx[3],
                    'ai_label': ai_label
                }

                if trx[0] not in tron_list.keys() and trx[0] not in random_walk_list.keys():
                    write_json(json_file_path='./random_walk_list.json', data=buffer, address=trx[0])

                print('dfs phase')
                print(trx)
                print(ai_label)
                print('-' * 50)

                element_list.append(trx)
                visited.add(trx[0])
            else:
                continue

            if len(element_list) > max_element:
                return element_list
        else:
            print('{} pass'.format(trx[0]))
            continue

        if len(element_list) > max_element:
            return element_list

        dfs(start_address=element_list[-1][0], visited=visited, element_list=element_list,\
            max_element=max_element, headers=headers, params=params,\
            pages=pages
           )
    
    return element_list
#
def bfs(start_address: str, visited: set, element_list: List,
        headers: str, params: dict, pages: int):

    params['address'] = start_address

    visited.add(start_address)

    dfs_total_trx = get_tronscan_feature.get_trx_from_tronscan(headers, params, pages)
    total_trx_simplfied = func_1(address=start_address, total_trx=dfs_total_trx)

    for trx in total_trx_simplfied:
        if trx[0] not in visited:

            if trx[0] == 'TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t':
                continue

            balance_now = get_time_and_balance(address=trx[0])[1]
            trx.append(balance_now)

            ai_label = get_ai_label(address=trx[0])

            if list(ai_label.keys())[0] == 'exchange' or list(ai_label.keys())[0] == 'kyc':
                buffer = {}

                buffer[trx[0]] = {
                    'receive_send': trx[1],
                    'trx_value': trx[2],
                    'balance': trx[3],
                    'ai_label': ai_label
                }

                if trx[0] not in tron_list.keys() and trx[0] not in random_walk_list.keys():
                    write_json(json_file_path='./random_walk_list.json', data=buffer, address=trx[0])

                print('bfs phase')
                print(trx)
                print(ai_label)
                print('-' * 50)

                trx.append(balance_now)
                element_list.append(trx)
                visited.add(trx[0])
            else:
                continue
        else:
            print('{} pass'.format(trx[0]))
            continue

    return element_list
#
def sort_trx(total_trx_simplfied):
    buffer = []

    for address in total_trx_simplfied.keys():
        temp = [
            address,\
            total_trx_simplfied[address]['receive_send'],\
            total_trx_simplfied[address]['value'],\
        ]

        buffer.append(temp)
    
    buffer_sorted = sorted(buffer, key=lambda x: x[2], reverse=True)

    return buffer_sorted
#
def get_time_and_balance(address):
    url_data = [
        'https://tron-rpc.publicnode.com/wallet/getaccount',
        'http://192.168.200.59:8090/wallet/getaccount',
        'http://192.168.200.145:8090/wallet/getaccount',
    ]
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    }
    data = {
        'address': address,
        'visible': True
    }

    for url in url_data:
        response = requests.post(url, headers=headers, data=json.dumps(data))

        if response.status_code == 200:
           result = response.json()
           wallet_address_create_time = result.get('create_time', 0)
           wallet_address_balance_now = result.get('balance', 0)/(10 ** 6) * 0.12

           return wallet_address_create_time, wallet_address_balance_now
        else:
            print('Request failed with status code', response.status_code)
            print(response.text)
#
def readJson(path: str):
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

    print('數據已寫入json')
#
def get_ai_label(address):
    url = f'http://localhost:8888/func_1?address={address}'
    response = requests.get(url)
    
    return response.json()
#
def func_1(address, total_trx):
    '''
    {
        address:{
            from_to: ...,
            value: ...,
        }
    }
    '''
    usdt_flag = False
    buffer = {}

    for i, trx in enumerate(total_trx):
        if trx['toAddressList'] == []:
            continue
        if i == len(total_trx) - 1:
            first_trx = trx['timestamp'] / (10 ** 3)
        if i == 0:
            last_trx = trx['timestamp'] / (10 ** 3)

        if trx['ownerAddress'] == 'TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t' or trx['toAddress'] == 'TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t': #usdt
            usdt_flag = True
            try:
                trx_value = int(trx['trigger_info']['parameter']['_value']) / (10 ** 6)
            except:
                try:
                    trx_value = int(trx['trigger_info']['data'][-64:], 16) / (10 ** 6)
                except:
                    trx_value = int(trx['amount']) / (10 ** 7)
        else: #trx
            usdt_flag = False
            trx_value = int(trx['amount']) / (10 ** 7)

        if trx_value > 1.1e+20:
            continue

        if usdt_flag:
            try:
                if address == trx['trigger_info']['parameter']['_to']: #receive, -
                    other_side_address = trx['trigger_info']['parameter']['_to']
                    from_to = 'send_side'
                else: #send, +
                    other_side_address = trx['trigger_info']['parameter']['_from']
                    from_to = 'recceive_side'
            except:
                if address == trx['ownerAddress']: #send, +
                    other_side_address = trx['toAddress']
                    from_to = 'recceive_side'
                else: #receive, -
                    other_side_address = trx['ownerAddress']
                    from_to = 'send_side'
        else:
            if address == trx['ownerAddress']: #send, +
                other_side_address = trx['toAddress']
                from_to = 'recceive_side'
            else: #receive, -
                other_side_address = trx['ownerAddress']
                from_to = 'send_side'

        buffer[other_side_address] = {'receive_send': from_to, 'value': trx_value}

    buffer_sorted = sort_trx(buffer)

    return buffer_sorted
#
def main(address):
    global tron_list
    global visited
    global random_walk_list

    headers = {'Api-Key': '444658e7-aa37-4e5c-98bf-646b7b085228'}
    params = {
        'sort': '-timestamp',
        'count': 'true',
        'limit': 50,
        'start': 0,
        'start_timestamp': 1546272000000,
        'direction': None,
        'end_timestamp': int(time.time() * 1000),
        'address': address
        }
    pages = int(100 / 50)

    tron_list = readJson('./label_database/tron.json')
    random_walk_list = readJson('./random_walk_list.json')

    visited = set()
    queue = []
    queue.append(address)

    while True:
        while queue:
            address = queue.pop(0)

            '''
            dfs_list = dfs(start_address=address, visited=visited, element_list=[],\
                        max_element=2, headers=headers, params=params,\
                        pages=pages,
                        )

            print('dfs phase done')
            '''

            dfs_list = [address]

            for address in dfs_list:
                #address = address[0]

                bfs_list = bfs(start_address=address, visited=visited, element_list=[],\
                            headers=headers, params=params, pages=pages
                            )
                
                for _ in bfs_list:
                    queue.append(_[0])

            print('bfs phase done')
#
if __name__ == '__main__':
    main(address='TXFBqBbqJommqZf7BV8NNYzePh97UmJodJ')
#