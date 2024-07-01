# 概述
此專案是 Tron 的爬蟲程序，主要是從 Tronscan 網站爬取數據，目的是通過已知的 Exchange 地址爬取更多的 Exchange 地址，以提升機器學習模型的分類準確度。

核心思想是與 Exchange 地址交易的對象有很大機率是 KYC 地址或是 Exchange 地址，所以對其交易對象進行遍歷並設置條件判斷應該可以找出其他的 Exchange 地址。

由於各種原因將之前用的機器學習模型覆蓋了，所以無法用模型幫助判斷。應只需註解掉 `get_ai_label()` 的部分，再以 `get_time_and_balance()` 獲取該地址餘額可以初步判斷是否為 Exchange 地址，其餘額通常很大，之前爬取的結果儲存在 `random_walk_list.json`。

# 算法步驟
1. 從 `tron.json` 取一 Exchange Hot（交易所）地址。
2. 設置請求參數，發出請求至 Tronscan 獲取該地址相關交易。
3. 通過 BFS 或是 DFS + BFS 算法爬取交易，通過現有的機器學習模型判斷是否為 Exchange 的地址，並存入隊列（queue）。
4. 只要隊列不為空則重複步驟 2 和步驟 3。

# Future Work
1. 目前公司主要以 Neo4j 圖數據庫存儲區塊鏈數據，主要有 BTC、ETH、TRON。圖像數據庫的存取速度較快，但目前數據都還在同步中，所以數據並不完整。

2. 當前目標是將此專案的算法應用到 Neo4j 圖數據庫上並改進算法結果，因此需要學習的內容包括但不限於：
   - Neo4j 網頁 UI 使用
   - Neo4j 的查詢語法 - Cypher
   - 各區塊鏈在 Neo4j 的存儲結構
   - 研究隨機遊走算法等

3. 目前基於 Neo4j 數據訓練好的機器學習模型只有 BTC，可先從此鏈開始研究，可參考 Ref 2.。

# Discussion
## 2024.06.26
### Participants
Jace, Allen
### Contents
1. 對BFS、DFS、Random Walk(BFS + DFS)做評測
2. 評測依據：AI模型預測出現'Exchange'佔的比例
3. 將 Queue 內容輸出成檔案儲存

# Data Format

1. **Misttrack API Labels**: If labels are obtained through the Misttrack API, add the fields `misttrack_label_list` and `misttrack_label_type`.
2. **AI Model Labels**: If no labels are obtained through Misttrack, use AI model judgment and write the results into the `bcs_label` field.

```json
{
  "bc1qajn9nr0f90zd2z20kgdwyy34e247g0v6alvpz6": {
    "degree": {
      "in_degree": 182,
      "out_degree": 147
    },
    "ai_label": {
      "Kyc": "50.47800064086914%",
      "Others": "26.714000701904297%",
      "Exchange": "22.808000564575195%"
    },
    "misttrack_label_list": [
      "binance",
      "deposit"
    ],
    "misttrack_label_type": "exchange",
    "bcs_label": "Exchange"
  },
  "1PFtVxKG3o8Devy6JVExKxFre6UMwDfpTM": {
    "degree": {
      "in_degree": 57,
      "out_degree": 55
    },
    "ai_label": {
      "Kyc": "57.176998138427734%",
      "Others": "21.525999069213867%",
      "Exchange": "21.297000885009766%"
    },
    "bcs_label": "Kyc"
  }
  // and so on...
}
```

### 說明

- **degree**: 包含 `in_degree` 和 `out_degree`。
- **ai_label**: 使用 AI 模型進行標籤判斷，並提供各類標籤的百分比。
- **misttrack_label_list**: 來自 Misttrack API 的標籤列表。
- **misttrack_label_type**: 來自 Misttrack API 的標籤類型。
- **bcs_label**: 如果無法從 Misttrack 獲取標籤，則使用 AI 模型的判斷結果。

# Reference
1. Neo4j 數據庫地址
   - 帳號：reader
   - 密碼：P@ssw0rd

   - BTC: [http://192.168.200.83:7474/](http://192.168.200.83:7474/) (bitcoin, bitcoin2, bitcoin3, bitcoin4, bitcoin5, bitcoin6, bitcoinv)
   - ETH: [http://192.168.200.73:7474/](http://192.168.200.73:7474/) (ethereum)
   - TRON: [http://192.168.200.196:7474](http://192.168.200.196:7474) (tron)

   * 對 Neo4j 有疑問可以問 Dustin。
   * 算法可以找 Ray 討論一下。

2. BTC 獲取 address 交易並取出真正交易值的 query
    ```cypher
    query_1 = '''
    MATCH (a:account {address: "%s"})<-[:output]-(t1:transaction)
    WITH t1.hash AS hash, a.address AS address, t1.timestamp AS timestamp, t1 AS transaction, "receive" AS direction
    RETURN hash, address, timestamp, direction
    UNION
    MATCH (a:account {address: "%s"})-[:input]->(t2:transaction)
    WITH t2.hash AS hash, a.address AS address, t2.timestamp AS timestamp, t2 AS transaction, "send" AS direction
    RETURN hash, address, timestamp, direction
    ''' % (address, address)

    query_2 = '''
    UNWIND $sorted_results AS record
    MATCH (transaction:transaction)
    WHERE transaction.hash = record['hash'] AND transaction.timestamp = record['timestamp'] AND "receive" = record['direction']
    OPTIONAL MATCH (a:account {address: "%s"})<-[r1:output]-(transaction)
    RETURN record.hash AS hash, record.address AS address, record.timestamp AS timestamp,
           record.direction AS direction, r1.value AS value
    UNION
    UNWIND $sorted_results AS record
    MATCH (transaction:transaction)
    WHERE transaction.hash = record['hash'] AND transaction.timestamp = record['timestamp'] AND "send" = record['direction']
    OPTIONAL MATCH (a:account {address: "%s"})-[r2:input]->(transaction)
    RETURN record.hash AS hash, record.address AS address, record.timestamp AS timestamp,
           record.direction AS direction, r2.value AS value
    ''' % (address, address)
    ```