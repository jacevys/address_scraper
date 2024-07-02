from dal_btc import Neo4jConnection
import requests
import inference_ml as ml
import json
import os
import argparse
import warnings

# 
def set_bcs_label(conn: Neo4jConnection, db_name: str, address: str, label: str):
    conn.set_bcs_label(db_name, address, label)
# 
def get_accounts(conn: Neo4jConnection, db_name: str, upper_bound: int, lower_bound: int, limit: int):
    return conn.get_address_by_degree(db_name, upper_bound, lower_bound, limit)
# 
def get_ai_label(address: str):
    result = ml.main(address=address)
    ai_label = 'Deposit' if list(result.keys())[0].title() == 'Kyc' else list(result.keys())[0].title()
    return f'Unknown {ai_label}'
#
def get_misttrack_label(coin: str, address: str) -> None:
    mapping = {'BTC': 'BTC', 'ETH': 'ETH', 'TRON': 'TRX'}
    api_key_mt = 'd8ab0f7a43cc49618af572fa6c5e1c0c'
    url = ('https://openapi.misttrack.io/v1/address_labels?coin={}&address={}&api_key={}'
           .format(mapping[coin], address, api_key_mt))

    try:
        response = requests.get(url=url, timeout=10).json()
        write_json('misttrack.json', data={address: {"mistrack_result": response['data']}}, address=address)
        try:
            label_list = []
            label_list.append(response['data']['label_list'][0])
            label_list.append(response['data']['label_type'].title())
            print(label_list)

            if response['data']['label_type'] == 'exchange' and 'deposit' in response['data']['label_list']:
                label_list[1] = 'Deposit'

            label = ' '.join(label_list).title()
        except:
            label = 'Unknown Unknown'
    except:
        label = 'Unknown'

    return label
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
# 
def set_label_proc(db_name: str, upper_bound: int, lower_bound: int, batch: int, get_label_method: str):
    # Connection details
    uri = "bolt://192.168.200.83:7687/"
    user = "reader"
    password = "P@ssw0rd"
    conn = Neo4jConnection(uri=uri, user=user, password=password)

    if get_label_method == 'ai':
        for address, (in_degree, out_degree) in get_accounts(conn, db_name, upper_bound, lower_bound, batch).items():
            label = get_ai_label(address)
            print(f'Processing {address}, in_degree: {in_degree}, out_degree: {out_degree}, label_method: ai, label: {label}')
            # set_bcs_label(conn, db_name, address, label)
    elif get_label_method == 'misttrack':
        for address, (in_degree, out_degree) in get_accounts(conn, db_name, upper_bound, lower_bound, batch).items():
            label = get_misttrack_label('BTC', address)
            print(f'Processing {address}, in_degree: {in_degree}, out_degree: {out_degree}, label_method: misstrack, label: {label}')
            # set_bcs_label(conn, db_name, address, label)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--db_name', type=str, help='Database name', required=True)
    parser.add_argument('--upper_bound', type=int, help='Upper bound of degree', required=True)
    parser.add_argument('--lower_bound', type=int, help='Lower bound of degree', required=True)
    parser.add_argument('--limit', type=int, help='Limit of accounts', required=True)
    parser.add_argument('--get_label_method', type=str, help='Get label method', required=True)
    args = parser.parse_args()

    main(args.db_name, args.upper_bound, args.lower_bound, args.limit, args.get_label_method)