import argparse
import time
from typing import *
import json
import os
from dal_btc import Neo4jConnection
import inference_ml as ml
import utils
from concurrent.futures import ThreadPoolExecutor

QUEUE_LIMIT = 10 ** 6
TIME_LIMIT = 3600
DEPTH_LIMIT = 10

# Connection details
uri = "bolt://192.168.200.83:7687/"
user = "reader"
password = "P@ssw0rd"
conn = Neo4jConnection(uri=uri, user=user, password=password)

method = 'dfs'

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
def write_walk_list(db_name, address, method):
    in_degree, out_degree = conn.get_degree(db_name=db_name, address=address)
    ml_result = ml.main(address=address)
    write_data = {
            address: {
                "in_degree": in_degree,
                "out_degree": out_degree, 
                "ai_label": ml_result,
                "method": method
            }
        }
    json_file_path = f'./random_walk_list_{method}.json'
    write_json(json_file_path=json_file_path, data=write_data, address=address)
#
def dfs(db_name: str, start_address: str, visited: set, element_list: List, 
        max_element: int, max_depth: int):
    address = start_address
    # first_key = next(iter(ml_result))
    # if first_key == 'exchange' and address not in btc_list.keys() and address not in random_walk_list.keys():
    if address not in btc_list.keys() and address not in random_walk_list.keys():
        write_walk_list(db_name=db_name, address=address, method=method)
    
    # print(f"max_depth: {max_depth}")
    if max_depth == 0:
        return element_list

    neighbors = conn.get_neighbors(db_name=db_name, address=address, limit=NB_LIMIT)
    count = 0
    for neighbor in neighbors:
        if len(element_list) > max_element:
            break
        if neighbor not in visited and neighbor not in btc_list.keys() and neighbor not in random_walk_list.keys():
            element_list.append(neighbor)
            visited.add(neighbor)
            count += 1

    while count:
        # print(f"count: {count}")
        if len(element_list) > max_element:
            break
        elif time.time() - start_time > TIME_LIMIT:
            break
        address = element_list.pop(-1)
        print(f"Processing address: {address}")
        dfs(db_name=db_name, start_address=address, visited=visited, element_list=element_list,\
            max_element=max_element, max_depth=max_depth-1)
        count -= 1

    return element_list
#
def bfs(db_name: str, start_address: str, visited: set):
    element_list = []

    address = start_address
    # first_key = next(iter(ml_result))
    # if first_key == 'exchange' and address not in btc_list.keys() and address not in random_walk_list.keys():
    if address not in btc_list.keys() and address not in random_walk_list.keys():
        write_walk_list(db_name=db_name, address=address, method=method)

    neighbors = conn.get_neighbors(db_name=db_name, address=address, limit=NB_LIMIT)
    for neighbor in neighbors:
        if neighbor not in visited and neighbor not in btc_list.keys() and neighbor not in random_walk_list.keys():
            element_list.append(neighbor)

    return element_list
# 
def process_neighbor(neighbor):
    # Assuming ml.main is now an async function
    ml_result = ml.main(address=neighbor)
    return list(ml_result.keys())[0].title() == 'Kyc'
# 
def get_kyc_ratio(databases: list[str], address: str):
    total, kyc = 0, 0
    for db in databases:
        neighbors = conn.get_neighbors(db_name=db, address=address, limit=20)
        print(f"Address: {address}, Database: {db}, Number of neighbors: {len(neighbors)}")
        total += len(neighbors)

        # for neighbor in neighbors:
        #     ml_result = ml.main(address=neighbor)
        #     if list(ml_result.keys())[0].title() == 'Kyc':
        #         kyc += 1

        # Define a function to process each neighbor
        def process_neighbor(neighbor):
            ml_result = ml.main(address=neighbor)
            return list(ml_result.keys())[0].title() == 'Kyc'
        
        # Use ThreadPoolExecutor to parallelize the processing of neighbors
        with ThreadPoolExecutor(max_workers=10) as executor:
            results = list(executor.map(process_neighbor, neighbors))
        
        # Aggregate the results
        kyc += sum(results)
    return kyc / total if total != 0 else float('nan')
#
# def main(db_name: str, json_file_path: str):
def main():
    global btc_list
    global visited
    global random_walk_list
    global start_time

    start_time = time.time()
    btc_list = readJson('./label_database/btc.json')
    count, total_ratio = 0, 0
    for address in btc_list.keys():
        if btc_list[address]['misttrack_label_type'] == 'exchange' and 'hot' in btc_list[address]['misttrack_label_list']:
            ratio = get_kyc_ratio(databases=['bitcoin', 'bitcoin2', 'bitcoin5'], address=address)
            print(f"Address: {address}, KYC ratio: {ratio}")
            if ratio != float('nan'):
                total_ratio += ratio
                count += 1
    print(f"Total count: {count}, Total KYC ratio: {total_ratio}")
    print(f"Average KYC ratio: {total_ratio / count}")
    print(f'elapsed time: {time.time() - start_time} seconds')
    return
    random_walk_list = {}
    if os.path.exists('./random_walk_list_allen.json'):
        random_walk_list = readJson('./random_walk_list_allen.json')

    visited = set()
    queue = []
    # read address from pending_address.txt into queue
    if os.path.exists('pending_address.txt'):
        with open('pending_address.txt', 'r') as f:
            for line in f:
                # print(f"Adding address: {line.strip()}")
                queue.append(line.strip())
                visited.add(line.strip())
        with open('pending_address.txt', 'w') as f:
            pass
    queue.clear()

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

        while len(queue) > QUEUE_LIMIT // 2:
            address = queue.pop(0)
            write_walk_list(db_name=db_name, address=address, method=method)
            if time.time() - start_time > TIME_LIMIT:
                break

        if time.time() - start_time > TIME_LIMIT:
            break

    start_time = time.time()
    print(f'Start processing')
    addresses = conn.get_address_by_degree(db_name=db_name, upper_bound=float('inf'), lower_bound=10000, limit=10000)
    for address, (indegree, outdegree) in addresses.items():
        write_json(json_file_path=json_file_path, 
                   data={address: {"in_degree": indegree, "out_degree": outdegree}}, address=address)
        # ml_result = ml.main(address=address)
        # mistrack_result = utils.get_misttrack_label(coin='BTC', address=address)
        # write_json(json_file_path=f'./misttrack_test.json', 
        #            data={address: {"in_degree": indegree, "out_degree": outdegree, "ai_label": ml_result, "mistrack_result": mistrack_result['data']}}, address=address)
        # print(f"Address: {address}, Indegree: {indegree}, Outdegree: {outdegree}, AI Label: {ml_result}")
        # response = utils.get_misttrack_label(coin='BTC', address=address)
    end_time = time.time()
    print(f'elapsed time: {end_time - start_time} seconds')

    with open('pending_address.txt', 'a') as f:
        for address in queue:
            f.write(address + '\n')

    # print(f"method: {method} done, processed time: {TIME_LIMIT}")

#
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run the blockchain address processing script.')
    # parser.add_argument('--db-name', type=str, help='Database name', required=True)
    # parser.add_argument('--file-path', type=str, help='JSON file path', required=True)
    # parser.add_argument('--method', type=str, help='Method to be used for processing addresses (bfs or dfs)', required=True)
    # parser.add_argument('--time-limit', type=int, help='Time limit for processing in seconds', required=True)
    args = parser.parse_args()
    # method = args.method
    # TIME_LIMIT = args.time_limit

    # main(args.db_name, args.file_path)
    main()
#