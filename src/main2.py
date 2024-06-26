import requests
import get_tronscan_feature
import time
import numpy as np
from typing import *
import json
import os
import dal_btc as btc
import inference_ml as ml

NB_LIMIT = 1000
QUEUE_LIMIT = 10 ** 9
TIME_LIMIT = 180
DEPTH_LIMIT = 10

method = 'dfs'

#
def dfs(db_name: str, start_address: str, visited: set, element_list: List, 
        max_element: int, max_depth: int):
    address = start_address
    ml_result = ml.main(address=address)
    first_key = next(iter(ml_result))
    if first_key == 'exchange' and address not in btc_list.keys() and address not in random_walk_list.keys():
    # if address not in btc_list.keys() and address not in random_walk_list.keys():
        in_degree, out_degree = btc.get_degree(db_name=db_name, address=address)
        write_data = {
            address: {
                "in_degree": in_degree,
                "out_degree": out_degree, 
                "ai_label": ml_result,
                "method": "dfs"
            }
        }
        write_json(json_file_path='./random_walk_list_allen.json', data=write_data, address=address)
    
    # print max depth
    print(f"max_depth: {max_depth}")
    if max_depth == 0:
        return element_list

    neighbors = btc.get_neighbors(db_name=db_name, address=address, limit=NB_LIMIT)
    count = 0
    for neighbor in neighbors:
        if len(element_list) > max_element:
            break
        if neighbor not in visited and neighbor not in btc_list.keys() and neighbor not in random_walk_list.keys():
            element_list.append(neighbor)
            visited.add(neighbor)
            count += 1

    while count:
        print(f"count: {count}")
        if len(element_list) > max_element:
            break
        elif time.time() - start_time > TIME_LIMIT:
            break
        address = element_list.pop(-1)
        dfs(db_name=db_name, start_address=address, visited=visited, element_list=element_list,\
            max_element=max_element, max_depth=max_depth-1)
        count -= 1

    return element_list
#
def bfs(db_name: str, start_address: str, visited: set):
    element_list = []

    address = start_address
    ml_result = ml.main(address=address)
    first_key = next(iter(ml_result))
    # if first_key == 'exchange' and address not in btc_list.keys() and address not in random_walk_list.keys():
    if address not in btc_list.keys() and address not in random_walk_list.keys():
        in_degree, out_degree = btc.get_degree(db_name=db_name, address=address)
        write_data = {
            address: {
                "in_degree": in_degree,
                "out_degree": out_degree, 
                "ai_label": ml_result,
                "method": "bfs"
            }
        }
        write_json(json_file_path='./random_walk_list_allen.json', data=write_data, address=address)

    neighbors = btc.get_neighbors(db_name=db_name, address=address, limit=NB_LIMIT)
    for neighbor in neighbors:
        if neighbor not in visited and neighbor not in btc_list.keys() and neighbor not in random_walk_list.keys():
            element_list.append(neighbor)

    return element_list
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
def main():
    global btc_list
    global visited
    global random_walk_list
    global start_time

    btc_list = readJson('./label_database/btc.json')
    random_walk_list = {}
    if os.path.exists('./random_walk_list_allen.json'):
        random_walk_list = readJson('./random_walk_list_allen.json')

    # Connection details
    uri = "bolt://192.168.200.83:7687/"
    user = "reader"
    password = "P@ssw0rd"
    db_name = "bitcoin"

    # Connect to Neo4j
    btc.init_db(uri, user, password)

    visited = set()
    queue = []
    # read address from pending_address.txt into queue
    if os.path.exists('pending_address.txt'):
        with open('pending_address.txt', 'r') as f:
            for line in f:
                print(f"Adding address: {line.strip()}")
                queue.append(line.strip())
                visited.add(line.strip())
        with open('pending_address.txt', 'w') as f:
            pass

    start_time = time.time()
    while queue:
        address = queue.pop(0)
        print(f"Processing address: {address}")

        dfs_list = []
        if method == 'dfs':
            dfs_list = dfs(db_name=db_name, start_address=address, visited=visited, element_list=[], 
                        max_element=QUEUE_LIMIT // 2, max_depth=DEPTH_LIMIT)

            queue.extend(dfs_list)

            print('dfs phase done')
        elif method == 'bfs':
            dfs_list = [address]
            for address in dfs_list:
                bfs_list = bfs(db_name=db_name, start_address=address, visited=visited)
                
                for _ in bfs_list:
                    if len(queue) >= QUEUE_LIMIT:
                        break
                    queue.append(_)
                    visited.add(_)

            print('bfs phase done')

        if time.time() - start_time > TIME_LIMIT:
            break

    # Close the connection
    btc.close_db()

    with open('pending_address.txt', 'a') as f:
        for address in queue:
            f.write(address + '\n')

#
if __name__ == '__main__':
    main()
#