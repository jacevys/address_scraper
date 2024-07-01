import argparse
import json

#
def readJson(path: str):
    with open(path, 'r', encoding='utf-8-sig') as json_file:
        buffer = json.load(json_file)
    
    return buffer
# 
def get_exch_ratio(data) -> float:
    samples = len(data)
    exch_num = 0
    for address in data.keys():
        label = data[address]['ai_label']
        first_key = next(iter(label))
        if first_key == 'exchange':
            exch_num += 1
    return exch_num / samples
# 
def main(json_file: str):
    btc_list = readJson(json_file)
    exch_ratio = get_exch_ratio(btc_list)
    print(f"Number of samples: {len(btc_list)}, Exchange ratio: {exch_ratio}")
    

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--json_file', type=str, required=True)
    args = parser.parse_args()

    main(args.json_file)