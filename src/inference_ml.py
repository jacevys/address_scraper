import os
import numpy as np
import pickle
import json
import requests
import csv
import time
import multiprocessing
from datetime import datetime
from neo4j import GraphDatabase
#
def inference(model_name, address, return_function):
    global reversed_mapping
    label_mapping_1 = {'others': 0, 'exchange': 1, 'kyc': 2}
    reversed_mapping = {label_mapping_1[key]: key for key in label_mapping_1.keys()}
    manager = multiprocessing.Manager()
    label_dict = manager.dict({
        address: {},
        'judged': False
    })

    train_set, train_label = load_dataset(data_list='train_set_1.json', label_mapping=label_mapping_1)
    train_set, train_data_min, train_data_max = normalize(train_set, test_flag=False, data_min_in=None, data_max_in=None)

    result_queue = multiprocessing.Queue()
    process = multiprocessing.Process(target=get_feature, args=(address, result_queue, label_dict))
    process.start()
    process.join(timeout=5)

    if label_dict['judged']:
        return label_dict[address]
    elif process.is_alive():
        process.terminate()
        label_dict[address] = {'exchange': '80%', 'others': '15%', 'kyc': '5%', 'scam': '0%'}
        label_dict['judged'] = True

        return label_dict[address]
    else:
        data = result_queue.get()

        if data == {}:
           label_dict[address] = {'others': '90%', 'kyc': '5%', 'exchange': '5%', 'scam': '0%'}
           label_dict['judged'] = True

           return label_dict[address]
        else:
            test_set = preprocess_data(data=data, data_min=train_data_min, data_max=train_data_max)

            model = loadPkl(f'./model/{model_name}.pkl')
            test_prob = convertPercentage(model.predict_proba(test_set))
            result = return_function(test_prob)
            label_dict[address] = result
            label_dict['judged'] = True

            return label_dict[address]
#
def get_degree(uri: str, username: str, password: str, databases: str, address: str) -> int:
    query = '''
    MATCH (a:account {address: $address})
    RETURN 
    a.address AS address,
    size([(a)<--() | 1]) AS in_degree, 
    size([(a)-->() | 1]) AS out_degree
    '''

    parameters = {
        'address': address,
    }

    counter: int = 0

    for database in databases:    
        driver = GraphDatabase.driver(uri, auth=(username, password), database=database)

        with driver.session() as session:
            query_result = session.run(query, parameters)
            result = [dict(record) for record in query_result]

        if result == []:
            continue
        else:
            counter += (result[0]['in_degree'] + result[0]['out_degree'])

    return counter
#
def get_feature(address: str, queue: object, label_dict: object) -> None:
    uri = 'bolt://192.168.200.83:7687'
    username = 'reader'
    password = 'P@ssw0rd'
    databases = ['bitcoin5', 'bitcoin', 'bitcoin2']

    total_degree = get_degree(uri=uri, username=username, password=password, databases=databases, address=address)

    if total_degree > 10000:
        label_dict[address] = {'exchange': '90%', 'others': '5%', 'kyc': '5%', 'scam': '0%'}
        label_dict['judged'] = True

        return

    total_receive, total_send, first_trx, last_trx = get_data(uri, username, password, databases, address)
    feature = calculate_feature(total_receive, total_send, first_trx, last_trx)

    queue.put(feature)
#
def convertPercentage(predictions):
    result = []

    for prediction in predictions:
        result.append(softmax(prediction))
    
    return result
#
def softmax(x):
    exp_x = np.exp(x)
    softmax_x = exp_x / np.sum(exp_x)

    return softmax_x
#
def return_result(probability_set):
    for i in range(len(probability_set)):
        result = sortProb(probability_set[i])

    return result
#
def loadPkl(path):
    with open(path, 'rb') as pkl_file:
        model = pickle.load(pkl_file)
    
    return model
#
def readJson(path: str):
    with open(path, 'r', encoding='utf-8-sig') as json_file:
        buffer = json.load(json_file)
    
    return buffer
#
def sortProb(prob):
    sorted_index = sorted(range(len(prob)), key=lambda i:prob[i], reverse=True)
    returned_result = {}

    for index in sorted_index:
        returned_result[reversed_mapping[index].title()] = f'{round(prob[index] * 100, 3)}%'

    return returned_result
#
def preprocess_data(data: dict, data_min: float, data_max: float) -> object:
    buffer = []

    for key in key_list:
        if key == 'Label':
            continue

        buffer.append(float(data[key]))
    
    buffer, temp_min, temp_max = normalize(buffer, True, data_min, data_max)

    return np.expand_dims(np.array(buffer), axis=0)
#
def load_dataset(data_list, label_mapping):
    dataset = []
    labelset = []

    json_list = readJson(f'./model_data/{data_list}')

    for i, key_1 in enumerate(json_list.keys()):
        temp = []

        if len(json_list[key_1].keys()) < len(key_list):
            continue

        for key_2 in key_list:
            temp.append(json_list[key_1][key_2])

        if temp[-1] not in label_mapping.keys():
            continue

        dataset.append(temp[:-1])
        labelset.append(label_mapping[temp[-1]])

    dataset, labelset = np.array(dataset), np.array(labelset)
    dataset, labelset = dataset.astype(np.float32), labelset.astype(np.int64)

    return dataset, labelset
#
def normalize(dataset=None, test_flag=None, data_min_in=None, data_max_in=None):
    min_value = 1
    max_value = 1000

    if test_flag:
        data_min = data_min_in
        data_max = data_max_in
    else:
        data_min = dataset.min(axis=0)
        data_max = dataset.max(axis=0)

    dataset = min_value + ((max_value - min_value) * (dataset - data_min)) / (data_max - data_min)
    dataset[np.isnan(dataset)] = 1000

    return dataset, data_min, data_max
#
def get_data(uri: str, username: str, password: str, databases: list, address: str):
    query_1 = '''
    MATCH (a:account {address: "%s"})<-[:output]-(t1:transaction)
    WITH t1.hash AS hash, a.address AS address, t1.timestamp AS timestamp, t1 AS transaction, "receive" AS direction
    RETURN hash, address, timestamp, direction
    UNION
    MATCH (a:account {address: "%s"})-[:input]->(t2:transaction)
    WITH t2.hash AS hash, a.address AS address, t2.timestamp AS timestamp, t2 AS transaction, "send" AS direction
    RETURN hash, address, timestamp, direction
    ''' % (address, address)

    query_2 = '''
    UNWIND $sorted_results AS record
    MATCH (transaction:transaction)
    WHERE transaction.hash = record['hash'] AND transaction.timestamp = record['timestamp'] AND "receive" = record['direction']
    OPTIONAL MATCH (a:account {address: "%s"})<-[r1:output]-(transaction)
    RETURN record.hash AS hash, record.address AS address, record.timestamp AS timestamp,
           record.direction AS direction, r1.value AS value
    UNION
    UNWIND $sorted_results AS record
    MATCH (transaction:transaction)
    WHERE transaction.hash = record['hash'] AND transaction.timestamp = record['timestamp'] AND "send" = record['direction']
    OPTIONAL MATCH (a:account {address: "%s"})-[r2:input]->(transaction)
    RETURN record.hash AS hash, record.address AS address, record.timestamp AS timestamp,
           record.direction AS direction, r2.value AS value
    ''' % (address, address)

    visited_hash = set()
    receive_trx_list = []
    send_trx_list = []

    for database in databases:
        driver = GraphDatabase.driver(uri, auth=(username, password), database=database)

        with driver.session() as session:
            result_1 = session.run(query_1)
            query_result_1 = [dict(record) for record in result_1]

        with driver.session() as session:
            result_2 = session.run(query_2, sorted_results=query_result_1)
            query_result_2 = [dict(record) for record in result_2]

        for record in query_result_2:
            if (record['direction'], record['hash']) not in visited_hash and record['value'] != None:
                if record['direction'] == 'receive':
                    visited_hash.add(('receive', record['hash']))
                    receive_trx_list.append(record)
                else:
                    visited_hash.add(('send', record['hash']))
                    send_trx_list.append(record)

    receive_trx_list_sorted = sort_by_timestamp(receive_trx_list)
    send_trx_list_sorted = sort_by_timestamp(send_trx_list)

    if receive_trx_list_sorted == [] and send_trx_list_sorted == []:
        return receive_trx_list_sorted, send_trx_list_sorted, 0, 0
    elif receive_trx_list_sorted == []:
        first_trx_timestamp = send_trx_list_sorted[-1]['timestamp']
        last_trx_timestamp =  send_trx_list_sorted[0]['timestamp']
    elif send_trx_list_sorted == []:
        first_trx_timestamp = receive_trx_list_sorted[-1]['timestamp']
        last_trx_timestamp =  receive_trx_list_sorted[0]['timestamp']
    else:
        first_trx_timestamp = min(receive_trx_list_sorted[-1]['timestamp'], send_trx_list_sorted[-1]['timestamp'])
        last_trx_timestamp = max(receive_trx_list_sorted[0]['timestamp'], send_trx_list_sorted[0]['timestamp'])

    receive_trx_list = [(trx['value'] / (10 ** 8)) * 61000 for trx in receive_trx_list_sorted]
    send_trx_list = [(trx['value'] / (10 ** 8)) * 61000 for trx in send_trx_list_sorted]

    return receive_trx_list, send_trx_list, first_trx_timestamp, last_trx_timestamp
#
def sort_by_timestamp(data: list):
    sorted_data = sorted(data, key=lambda x: x['timestamp'], reverse=True)

    return sorted_data
#
def calculate_feature(total_receive: list, total_send: list, first_trx: float, last_trx: float):
    if total_receive == []:
        total_receive_numpy = [0]
    else:
        total_receive_numpy = total_receive
    if total_send == []:
        total_send_numpy = [0]
    else:
        total_send_numpy = total_send

    if (len(total_receive) + len(total_send)) <= 0:
        return {}

    total_receive_numpy = np.array(total_receive_numpy)
    total_send_numpy = np.array(total_send_numpy)
    feature = {}

    feature['First_Transaction_Date'] = int(first_trx)
    feature['Last_Transaction_Date'] = int(last_trx)
    feature['Life_Span'] = int(last_trx - first_trx)
    feature['Period'] = int(last_trx - first_trx) / (len(total_receive) + len(total_send))
    feature['Balance'] = float(np.sum(total_receive_numpy)) - float(np.sum(total_send_numpy))
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
def main(address):
    global key_list

    key_list = [
        'Life_Span', 'Period',
        'Total_Transaction_Times', 'Total_Times_Receive', 'Total_Times_Send',
        'Total_Value_Receive', 'Max_Value_Receive', 'Min_Value_Receive',
        'Average_Value_Receive', 'Median_Value_Receive', 'Std_Deviation_Receive',
        'Total_Value_Send', 'Max_Value_Send', 'Min_Value_Send',
        'Average_Value_Send', 'Median_Value_Send', 'Std_Deviation_Send',
        'Label'
    ]

    # print(f'address: {address}')

    result = inference(model_name='btc_xgb_1', address=address, return_function=return_result)

    # print(f'pred: {result}')
    # print('#' * 100)
    return result
#
if __name__ == '__main__':
    main(address='1FWQiwK27EnGXb6BiBMRLJvunJQZZPMcGd')
#