from dal_btc import Neo4jConnection
import inference_ml as ml
from concurrent.futures import ThreadPoolExecutor
import utils
import time
import math

# Connection details
uri = "bolt://192.168.200.83:7687/"
user = "reader"
password = "P@ssw0rd"
conn = Neo4jConnection(uri=uri, user=user, password=password)

# 
def get_kyc_ratio(databases: list[str], address: str, json_file_path: str):
    total, kyc = 0, 0
    for db in databases:
        neighbors = conn.get_neighbors(db_name=db, address=address, limit=10 ** 4)
        print(f"Address: {address}, Database: {db}, Number of neighbors: {len(neighbors)}")
        total += len(neighbors)

        for neighbor in neighbors:
            if neighbor in visited_list.keys():
                label = list(visited_list[neighbor]['ai_label'].keys())[0].title()
                if label == 'Kyc' or label == 'Exchange':
                    kyc += 1
        neighbors = [neighbor for neighbor in neighbors if neighbor not in visited_list.keys()]

        # Define a function to process each neighbor
        def process_neighbor(neighbor):
            return neighbor, ml.main(address=neighbor)
        
        # Use ThreadPoolExecutor to parallelize the processing of neighbors
        with ThreadPoolExecutor(max_workers=10) as executor:
            results = list(executor.map(process_neighbor, neighbors))
        
        # Aggregate the results
        for neighbor, ml_result in results:
            if list(ml_result.keys())[0].title() == 'Kyc' or list(ml_result.keys())[0].title() == 'Exchange':
                kyc += 1
            # in_degree, out_degree = conn.get_degree(db_name=db, address=neighbor)
            # utils.write_json(json_file_path=json_file_path, 
            #            data={neighbor: {
            #                     "in_degree": in_degree, 
            #                     "out_degree": out_degree, 
            #                     "ai_label": ml_result
            #                    }
            #             }, address=neighbor)
    return kyc / total if total != 0 else float('nan')
# 
def main():
    global visited_list

    btc_list = utils.readJson('./label_database/btc.json')
    visited_file_path = './visited_list.json'
    visited_list = {}
    visited_list = utils.readJson(visited_file_path)
    databases = ['bitcoin', 'bitcoin2', 'bitcoin5']

    if len(visited_list) > 10 ** 8:
        remove_list = list(visited_list.keys())[:len(visited_list) // 2]
        utils.remove_keys_from_json(json_file_path=visited_file_path, keys=remove_list)
        return

    start_time = time.time()
    count, total_ratio = 0, 0
    for address in btc_list.keys():
        if btc_list[address]['misttrack_label_type'] == 'exchange' and 'hot' in btc_list[address]['misttrack_label_list']:
            ratio = get_kyc_ratio(databases=databases, address=address, json_file_path=visited_file_path)
            print(f"Address: {address}, KYC ratio: {ratio}")
            if not math.isnan(ratio):
                total_ratio += ratio
                count += 1
    avg_ratio = total_ratio / count if count != 0 else float('nan')
    print(f"Total count: {count}, Total KYC ratio: {total_ratio}, Average KYC ratio: {avg_ratio}")
    print(f'elapsed time for computing KYC ratio: {time.time() - start_time} seconds')

    with open('kyc_ratio.txt', 'w') as f:
        f.write(f"Average KYC ratio: {avg_ratio}")
    
if __name__ == '__main__':
    main()