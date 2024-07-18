from dal_btc import Neo4jConnection
import utils
import time

# Connection details
uri = "bolt://192.168.200.83:7687/"
user = "reader"
password = "P@ssw0rd"
conn = Neo4jConnection(uri=uri, user=user, password=password)

# 
def main():
    # databases = ['bitcoin', 'bitcoin2', 'bitcoin5']
    databases = ['bitcoin5']

    visited_file_path = './visited_list.json'
    visited_list = {}
    # visited_list = utils.readJson(visited_file_path)
    misttrack_pending_file_path = './misttrack_pending_list.json'

    if len(visited_list) > 10 ** 8:
        remove_list = list(visited_list.keys())[:len(visited_list) // 2]
        utils.remove_keys_from_json(json_file_path=visited_file_path, keys=remove_list)

    start_time = time.time()
    count = 0
    for db_name in databases:
        addresses = conn.get_address_by_degree(db_name=db_name, lower_bound=10000, limit=10 ** 8)
        count += len(addresses)
        for address, (indegree, outdegree) in addresses.items():
            # utils.write_json(json_file_path=visited_file_path, 
            #            data={address: {
            #                     "in_degree": indegree, 
            #                     "out_degree": outdegree, 
            #                     "ai_label": {
            #                         'exchange': '90%', 
            #                         'others': '5%', 
            #                         'kyc': '5%', 
            #                         'scam': '0%'
            #                         }
            #                    }
            #             }, address=address)
            utils.write_json(json_file_path=misttrack_pending_file_path, 
                       data={address: {
                                "in_degree": indegree, 
                                "out_degree": outdegree, 
                               }
                        }, address=address)
            print(f'Processing {address}, in_degree: {indegree}, out_degree: {outdegree}')
    print(f'number of list items: {count}')
    print(f'elapsed time for generating pending list: {time.time() - start_time} seconds')
    
if __name__ == '__main__':
    main()