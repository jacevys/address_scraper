import numpy as np
import pickle
import json
import time
import multiprocessing
from datetime import datetime
from typing import *
from neo4j import GraphDatabase
#
def inference(model_name, address, return_function):
    global reversed_mapping
    label_mapping_1 = {'others': 0, 'kyc': 1, 'scam': 2}
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
        returned_result[reversed_mapping[index]] = f'{round(prob[index] * 100, 3)}%'

    return returned_result
#
def load_dataset(data_list, label_mapping):
    dataset = []
    labelset = []

    json_list = readJson(f'./data/{data_list}')

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
def get_data(uri: str, username: str, password: str, database: str, address: str) -> \
    Tuple[List[object], List[float], List[float], float, float]:
    query = '''
    CALL{
    MATCH (a:account {address: $address})<--(t1:transaction)<-[:includes]-(b1:block)
    WITH t1.hash AS hash, b1.timestamp AS timestamp, t1.transaction_index AS token_address, t1.value AS value, 'transaction' AS trx_type, 'receive' AS receive_send
    RETURN hash, timestamp, token_address, value, trx_type, receive_send
    LIMIT $limit
    UNION
    MATCH (a:account {address: $address})-->(t2:transaction)<-[:includes]-(b2:block)
    WITH t2.hash AS hash, b2.timestamp AS timestamp, t2.transaction_index AS token_address, t2.value AS value, 'transaction' AS trx_type, 'send' AS receive_send
    RETURN hash, timestamp, token_address, value, trx_type, receive_send
    LIMIT $limit
    UNION
    MATCH (a:account {address: $address})<--(i3:internal_transaction)<-[:includes]-(n3)-[:includes]-(b3:block)
    WITH n3.hash AS hash, b3.timestamp AS timestamp, i3.step AS token_address, i3.value AS value, 'internal_transaction' AS trx_type, 'receive' AS receive_send
    RETURN hash, timestamp, token_address, value, trx_type, receive_send
    LIMIT $limit
    UNION
    MATCH (a:account {address: $address})-->(i4:internal_transaction)<-[:includes]-(n4)-[:includes]-(b4:block)
    WITH n4.hash AS hash, b4.timestamp AS timestamp, i4.step AS token_address, i4.value AS value, 'internal_transaction' AS trx_type, 'send' AS receive_send
    RETURN hash, timestamp, token_address, value, trx_type, receive_send
    LIMIT $limit
    UNION
    MATCH (a:account {address: $address})<--(t5:token_transfer)<-[:includes]-(n5)-[:includes]-(b5:block)
    WITH n5.hash AS hash, b5.timestamp AS timestamp, t5.token_address AS token_address, t5.value AS value, 'token_transfer' AS trx_type, 'receive' AS receive_send
    RETURN hash, timestamp, token_address, value, trx_type, receive_send
    LIMIT $limit
    UNION
    MATCH (a:account {address: $address})<--(t6:token_transfer)<-[:includes]-(n6)-[:includes]-(b6:block)
    WITH n6.hash AS hash, b6.timestamp AS timestamp, t6.token_address AS token_address, t6.value AS value, 'token_transfer' AS trx_type, 'send' AS receive_send
    RETURN hash, timestamp, token_address, value, trx_type, receive_send
    LIMIT $limit
    }
    RETURN hash, timestamp, token_address, value, trx_type, receive_send
    LIMIT $limit
    '''

    parameters = {
        'address': address,
        'limit': 10 ** 6
    }

    total_receive: List[float] = []
    total_send: List[float] = []

    driver = GraphDatabase.driver(uri, auth=(username, password), database=database)

    with driver.session() as session:
        query_result = session.run(query, parameters)
        result = [dict(record) for record in query_result]

    result_sorted = sort_by_timestamp(result)

    if result_sorted == []:
        return result_sorted, total_receive, total_send, 0, 0

    first_trx = float(result_sorted[-1].get('timestamp')) / 1000
    last_trx = float(result_sorted[0].get('timestamp')) / 1000
    
    total_receive, total_send = classify_trx(result_sorted=result_sorted)

    return result_sorted, total_receive, total_send, first_trx, last_trx
#
def sort_by_timestamp(data: list):
    sorted_data = sorted(data, key=lambda x: x['timestamp'], reverse=True)

    return sorted_data
#
def classify_trx(result_sorted: list) -> Tuple[List[float], List[float]]:
    token_transfer_dict: Dict[str, int] = {
        'TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t': 10 ** 6,
        'TEkxiTehnzSmSe2XqrBj4w32RUN966rdz8': 10 ** 6
    }
    total_receive: List[float] = []
    total_send: List[float] = []

    for trx in result_sorted:
        if float(trx.get('timestamp')) > 1704067199000:
            continue

        trx_value: float = 0

        if trx.get('trx_type') == 'transaction':
            trx_value = float(trx.get('value')) / (10 ** 8)
        elif trx.get('trx_type') == 'internal_transaction':
            trx_value = float(trx.get('value')) / (10 ** 8)
        elif trx.get('trx_type') == 'token_transfer':
            if trx.get('token_address') not in token_transfer_dict.keys():
                continue
            else:
                trx_value = float(trx.get('value')) / token_transfer_dict[trx.get('token_address')]
        
        if trx.get('receive_send') == 'receive':
            total_receive.append(trx_value)
        else:
            total_send.append(trx_value)

    return total_receive, total_send
#
def calculate_feature(total_receive: list, total_send: list, first_trx: float, last_trx: float) -> Dict[str, float]:
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
def get_feature(address: str, queue: object, label_dict: object) -> None:
    uri = 'bolt://192.168.200.196:7687'
    username = 'reader'
    password = 'P@ssw0rd'
    database = 'tron'

    total_degree = get_degree(uri=uri, username=username, password=password, database=database, address=address)

    if total_degree > 50000:
        label_dict[address] = {'exchange': '90%', 'others': '5%', 'kyc': '5%', 'scam': '0%'}
        label_dict['judged'] = True

        return

    result_sorted, total_receive, total_send, first_trx, last_trx = get_data(uri, username, password, database, address)
    feature = calculate_feature(total_receive, total_send, first_trx, last_trx)

    queue.put(feature)
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
def get_degree(uri: str, username: str, password: str, database: str, address: str) -> int:
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

    driver = GraphDatabase.driver(uri, auth=(username, password), database=database)

    with driver.session() as session:
        query_result = session.run(query, parameters)
        result = [dict(record) for record in query_result]

    if result == []:
        return 0
    else:
        return result[0]['in_degree'] + result[0]['out_degree']
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

    print(f'address: {address}')

    result = inference(model_name='tron_xgb_1', address=address, return_function=return_result)

    print(f'pred: {result}')
    print('#' * 100)
    return result
#
def test():
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

    dataset = readJson(path='./data/exchange.json')
    err_counter = 0
    accumulate_time = 0

    for i, address in enumerate(dataset.keys()):
        if dataset[address] == {}:
            continue

        print(f'index: {i + 1}, address: {address}')

        start_time = time.time()

        result = inference(model_name='tron_xgb_1', address=address, return_function=return_result)
        
        end_time = time.time()
        total_time = end_time - start_time
        accumulate_time += total_time

        if list(result.keys())[0] != 'exchange':
            err_counter += 1

        print(f'pred: {result}')
        print(f'time: {total_time}')
        print(f'avg_time: {accumulate_time / (i + 1)}')
        print(f'err: {err_counter}')
        print('#' * 100)
#
if __name__ == '__main__':
    test()
#
'''
err
scam: 32 / ?
kyc: 69 / ?
others: 109 / ?
exhcange: 3 / 73
'''