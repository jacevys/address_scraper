from dal_btc import Neo4jConnection
import inference_ml_btc as ml
from concurrent.futures import ThreadPoolExecutor, as_completed
import utils
import time
import math
import asyncio

# Connection details
uri = "bolt://192.168.200.83:7687/"
user = "reader"
password = "P@ssw0rd"
conn = Neo4jConnection(uri=uri, user=user, password=password)

# 
def get_kyc_ratio(databases: list[str], address: str, json_file_path: str):
    start_time = time.time()

    total, kyc = 0, 0
    for db in databases:
        neighbors = conn.get_neighbors(db_name=db, address=address, limit=10 ** 3)
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
            try:
                return neighbor, asyncio.run(ml.main(address=neighbor))
            except Exception as e:
                print(f"Error processing neighbor: {neighbor}: {e}")
                return neighbor, None
        
        print('Start processing neighbors...')

        # Use ThreadPoolExecutor to parallelize the processing of neighbors
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_neighbor = [executor.submit(process_neighbor, neighbor) for neighbor in neighbors]
            results = []
            for future in as_completed(future_to_neighbor):
                try:
                    results.append(future.result())
                except Exception as e:
                    print(f"Error processing future: {e}")

        print('Finish processing neighbors.')
        
        # Aggregate the results
        for neighbor, ml_result in results:
            if ml_result is None:
                return float('nan')
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

    print(f'elapsed time for processing all neighbors: {time.time() - start_time} seconds')

    return kyc / total if total != 0 else float('nan')

# 
def main():
    global visited_list

    visited_file_path = './visited_list.json'
    visited_list = {}
    visited_list = utils.readJson(visited_file_path)
    misttrack_pending_file_path = './misttrack_pending_list.json'
    misttrack_list = utils.readJson(misttrack_pending_file_path)
    avg_ratio_file_path = './kyc_ratio.txt'
    avg_ratio = float('nan')
    misttrack_file_path = './misttrack_list.json'
    misttrack_exclued_file_path = './misttrack_excluded_list.json'
    with open(avg_ratio_file_path, 'r') as f:
        avg_ratio = float(f.read().split(': ')[1])
    if math.isnan(avg_ratio):
        print("No average KYC ratio found, please run kyc_ratio.py first.")
        return
    databases = ['bitcoin', 'bitcoin2', 'bitcoin5']

    if len(visited_list) > 10 ** 8:
        remove_list = list(visited_list.keys())[:len(visited_list) // 2]
        utils.remove_keys_from_json(json_file_path=visited_file_path, keys=remove_list)

    start_time = time.time()
    for address in misttrack_list.keys():
        kyc_ratio = get_kyc_ratio(databases=databases, address=address, json_file_path=visited_file_path)
        if math.isnan(kyc_ratio):
            print(f"Error processing address: {address}")
            break
        print(f"Address: {address}, KYC ratio: {kyc_ratio}")
        json_file_path = misttrack_file_path if kyc_ratio >= avg_ratio else misttrack_exclued_file_path
        utils.write_json(json_file_path=json_file_path, 
                    data={address: {
                            "in_degree": misttrack_list[address]['in_degree'], 
                            "out_degree": misttrack_list[address]['out_degree'], 
                            "kyc_ratio": kyc_ratio
                            }
                    }, address=address)
        utils.remove_keys_from_json(json_file_path=misttrack_pending_file_path, keys=[address])
    print(f'elapsed time for kyc verification: {time.time() - start_time} seconds')
                
    
if __name__ == '__main__':
    main()