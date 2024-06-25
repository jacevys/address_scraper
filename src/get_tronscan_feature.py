import numpy as np
import time
import json
import requests
import os
#
def readJson(path: str):
    with open(path, 'r', encoding='utf-8-sig') as json_file:
        buffer = json.load(json_file)
    
    return buffer
#
def get_trx_from_tronscan(headers, params, pages):
    api_url = 'https://apilist.tronscanapi.com/api/transaction'
    total_trx = []

    try:
        for _ in range(pages):
            response = requests.get(api_url, params=params, headers=headers)
            response.raise_for_status()
            data = response.json()
            trx = data.get('data', [])
            total_trx.extend(trx)
            params['start'] += params['limit']

        return total_trx

    except requests.exceptions.RequestException as e:
        print(f'Error making request: {e}')
#
def saveJson(save_path, wallet_list):
    with open(save_path, 'w') as json_file:
        json.dump(wallet_list, json_file, indent=2)

    print('saved')
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
def get_balance_and_time(address):
    url_data = ['https://tron-rpc.publicnode.com/wallet/getaccount',
                'http://192.168.200.197:8090/wallet/getaccount',
                'http://192.168.200.159:8090/wallet/getaccount',
                'http://192.168.200.145:8090/wallet/getaccount',
                'http://192.168.200.48:8090/wallet/getaccount',
                'http://192.168.200.182:8090/wallet/getaccount'
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
           wallet_address_create_time = result.get('create_time',0)
           wallet_address_balance_now = result.get('balance',0)/(10**6)*0.12

           return wallet_address_create_time, wallet_address_balance_now
        else:
            print('Request failed with status code', response.status_code)
            print(response.text)
#
def func_1(address, total_trx, key_list):
    balance_now = 0
    timestamp_prev = 0
    timestamp_now = 0
    coin = ''
    feature_buffer = {key: [] for key in key_list}

    for i, trx in enumerate(total_trx[::-1]):
        if trx['toAddressList'] == []:
            continue

        if trx['ownerAddress'] == 'TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t' or trx['toAddress'] == 'TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t': #usdt
            try:
                trx_value = int(trx['trigger_info']['parameter']['_value']) / (10 ** 6)
            except:
                try:
                    trx_value = int(trx['trigger_info']['data'][-64:], 16) / (10 ** 6)
                except:
                    trx_value = int(trx['amount']) / (10 ** 7)

            coin = 'usdt'
        else: #trx
            trx_value = int(trx['amount']) / (10 ** 7)
            coin = 'trx'

        if trx_value > 1.1e+20:
            continue

        timestamp_now = trx['timestamp'] / 1000

        if address == trx['ownerAddress']:
            receive_send = 'send'
            balance = -trx_value
        else:
            receive_send = 'receive'
            balance = trx_value

        if i == 0:
            balance_now = balance
            interval = 0
            timestamp_prev = timestamp_now
        else:
            balance_now += balance
            interval = timestamp_now - timestamp_prev
            timestamp_prev = timestamp_now

        feature_buffer['balance'].append(balance_now)
        feature_buffer['receive_send'].append(receive_send)
        feature_buffer['value'].append(trx_value)
        feature_buffer['interval'].append(interval)
        feature_buffer['coin'].append(coin)

    return feature_buffer
#
def func_2(address, total_trx):
    create_time, balance_now = get_balance_and_time(address)
    balance_list = [balance_now]
    usdt_flag = False
    total_receive = []
    total_send = []
    first_trx = 0
    last_trx = 0

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
                    total_receive.append(trx_value)
                    balance_list.append(balance_list[-1] - trx_value)
                else: #send, +
                    total_send.append(trx_value)
                    balance_list.append(balance_list[-1] + trx_value)
            except:
                if address == trx['ownerAddress']: #send, +
                    total_send.append(trx_value)
                    balance_list.append(balance_list[-1] + trx_value)
                else: #receive, -
                    total_receive.append(trx_value)
                    balance_list.append(balance_list[-1] - trx_value)
        else:
            if address == trx['ownerAddress']: #send, +
                total_send.append(trx_value)
                balance_list.append(balance_list[-1] + trx_value)
            else: #receive, -
                total_receive.append(trx_value)
                balance_list.append(balance_list[-1] - trx_value)

    balance_avg = np.mean(balance_list)

    return total_receive, total_send, first_trx, last_trx, balance_now, balance_avg, create_time
#
def func_3(address, total_receive, total_send, first_trx, last_trx, balance_now, balance_avg, create_time):
    if total_receive == []:
        total_receive_numpy = [0]
    else:
        total_receive_numpy = total_receive
    if total_send == []:
        total_send_numpy = [0]
    else:
        total_send_numpy = total_send

    total_receive_numpy = np.array(total_receive_numpy)
    total_send_numpy = np.array(total_send_numpy)
    feature = {}

    feature['Create_Time'] = int(create_time / (10 ** 3))
    feature['First_Transaction_Date'] = int(first_trx)
    feature['Last_Transaction_Date'] = int(last_trx)
    feature['Life_Span'] = int(last_trx - first_trx)
    feature['Period'] = int(last_trx - first_trx) / (len(total_receive) + len(total_send))
    feature['Balance_Now'] = balance_now
    feature['Average_Balance'] = balance_avg
    feature['Total_Transaction_Times'] = len(total_receive) + len(total_send)
    feature['Total_Times_Receive'] = len(total_receive)
    feature['Total_Times_Send'] = len(total_send)
    feature['Total_Value_Receive'] = float(np.sum(total_receive_numpy))
    feature['Max_Value_Receive'] = float(np.max(total_receive_numpy))
    feature['Min_Value_Receive'] = float(np.min(total_receive_numpy))
    feature['Average_Value_Receive'] = float(np.mean(total_receive_numpy))
    feature['Median_Value_Receive'] = float(np.median(total_receive_numpy))
    feature['Std_Deviation_Receive'] = float(np.std(total_receive_numpy))
    feature['Total_Value_Send'] = float(np.sum(total_send_numpy))
    feature['Max_Value_Send'] = float(np.max(total_send_numpy))
    feature['Min_Value_Send'] = float(np.min(total_send_numpy))
    feature['Average_Value_Send'] = float(np.mean(total_send_numpy))
    feature['Median_Value_Send'] = float(np.median(total_send_numpy))
    feature['Std_Deviation_Send'] = float(np.std(total_send_numpy))

    return feature
#
def main(category=None):
    data_list = readJson(f'./data/{category}_jace.json')
    headers = {'Api-Key': '444658e7-aa37-4e5c-98bf-646b7b085228'}
    params = {
        'sort': '-timestamp',
        'count': 'true',
        'limit': 50,
        'start': 0,
        'start_timestamp': 1546272000000,
        'direction': None,
        'end_timestamp': int(time.time() * 1000),
        'address': ''
        }
    pages = int(1000 / 50)
    key_list = [
        'balance',
        'receive_send',
        'value',
        'interval',
        'coin'
    ]

    for i, address in enumerate(data_list.keys()):
        buffer = {}
        params['address'] = address
        total_trx = get_trx_from_tronscan(headers, params, pages)
        total_receive, total_send, first_trx, last_trx, balance_now, balance_avg, create_time = func_2(address, total_trx)
        feature_buffer = func_3(address, total_receive, total_send, first_trx, last_trx, balance_now, balance_avg, create_time)
        params['start'] = 0
        buffer[address] = feature_buffer

        write_json(json_file_path=f'./data/{category}_jace_2.json', data=buffer, address=address)
        print(f'index: {i + 1}, address: {address}')
        print(feature_buffer)
        print('#' * 50)
#
if __name__ == '__main__':
    main(category='scam')
#