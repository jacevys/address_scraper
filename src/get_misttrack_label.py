import utils

# 
def main():
    btc_file_path = './label_database/btc.json'
    btc_list = {}
    btc_list = utils.readJson(btc_file_path)
    misttrack_file_path = './misttrack_list.json'
    misttrack_list = {}
    misttrack_list = utils.readJson(misttrack_file_path)

    for address in misttrack_list.keys():
        if address not in btc_list.keys():
            mistrack_result = utils.get_misttrack_label(coin='BTC', address=address)
            utils.write_json(json_file_path=btc_file_path, 
                   data={address: {'misttrack_label_list': mistrack_result['data']['label_list'], 'misttrack_label_type': mistrack_result['data']['label_type']}}, address=address)
# 
if __name__ == '__main__':
    main()