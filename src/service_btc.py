from dal_btc import Neo4jConnection
import inference_ml as ml
from concurrent.futures import ThreadPoolExecutor
import utils

class BTCService:
    def __init__(self, btc_dal: Neo4jConnection):
        self.btc_dal = btc_dal
        self.visited_list = utils.readJson('./visited_list.json')

    def get_kyc_ratio(databases: list[str], address: str, json_file_path: str):
        total, kyc = 0, 0
        for db in databases:
            neighbors = self.btc_dal.get_neighbors(db_name=db, address=address, limit=200)
            print(f"Address: {address}, Database: {db}, Number of neighbors: {len(neighbors)}")
            total += len(neighbors)

            for neighbor in neighbors:
                if neighbor in self.visited_list.keys():
                    label = list(self.visited_list[neighbor]['ai_label'].keys())[0].title()
                    if label == 'Kyc' or label == 'Exchange':
                        kyc += 1
            neighbors = [neighbor for neighbor in neighbors if neighbor not in self.visited_list.keys()]

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
                in_degree, out_degree = conn.get_degree(db_name=db, address=neighbor)
                utils.write_json(json_file_path=json_file_path, 
                        data={neighbor: {
                                    "in_degree": in_degree, 
                                    "out_degree": out_degree, 
                                    "ai_label": ml_result
                                }
                            }, address=neighbor)
        return kyc / total if total != 0 else float('nan')