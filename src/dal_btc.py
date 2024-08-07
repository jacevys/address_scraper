from neo4j import GraphDatabase
import time
import utils

class Neo4jConnection:
    
    def __init__(self, uri: str, user: str, password: str):
        self.__uri = uri
        self.__user = user
        self.__password = password
        self.__driver = None
        try:
            self.__driver = GraphDatabase.driver(self.__uri, auth=(self.__user, self.__password))
        except Exception as e:
            print("Failed to create the driver:", e)

    def __del__(self):
        if self.__driver is not None:
            self.__driver.close()
            # print("Driver closed")
    
    def get_degree(self, db_name: str, address: str):
        query = """
        MATCH (a:account {address: $node_address})
        RETURN a.address AS address, size([(a)<--() | 1]) AS in_degree, size([(a)-->() | 1]) AS out_degree
        """
    
        session = None
        response = None
        in_degree, out_degree = 0, 0
        try:
            session = self.__driver.session(database=db_name)
            response = list(session.run(query, parameters={"node_address": address}))
            if response:
                record = response[0]
                in_degree, out_degree = record['in_degree'], record['out_degree']

        except Exception as e:
            print("Query failed (get_degree):", e)
        finally:
            if session is not None:
                session.close()
        return in_degree, out_degree
    
    def get_neighbors(self, db_name: str, address: str, limit: int):
        query = """
        MATCH (ac:account {address: $node_address}) -[:input|output]-(:transaction)-[:input|output]-(an:account)
        WHERE ac <> an
        RETURN DISTINCT an.address AS neighbor_address
        LIMIT $limit
        """
    
        session = None
        response = None
        neighbors = []
        try:
            session = self.__driver.session(database=db_name)
            response = list(session.run(query, parameters={"node_address": address, "limit": limit}))
            for record in response:
                neighbors.append(record['neighbor_address'])
        except Exception as e:
            print("Query failed (get_neighbors):", e)
        finally:
            if session is not None:
                session.close()
        return neighbors
    
    def get_address_by_degree(self, db_name: str, lower_bound: int, limit: int):
        query = """
        MATCH (a:account)
        WITH a.address AS address, size([(a)<--() | 1]) AS in_degree, size([(a)-->() | 1]) AS out_degree
        WHERE (in_degree + out_degree) >= $lower_bound
        RETURN address, in_degree, out_degree
        LIMIT $limit
        """
    
        session = None
        response = None
        address_list = {}
        try:
            session = self.__driver.session(database=db_name)
            response = list(session.run(query, parameters={"lower_bound": lower_bound, "limit": limit}))
            for record in response:
                address_list[record['address']] = (record['in_degree'], record['out_degree'])
        except Exception as e:
            print("Query failed (get_address_by_degree):", e)
        finally:
            if session is not None:
                session.close()
        return address_list
    
    def set_bcs_label(self, db_name: str, address: str, label: str):
        query = """
        MATCH (a:account {address: $node_address})
        SET a.bcs_label = $label
        """
    
        session = None
        try:
            session = self.__driver.session(database=db_name)
            session.run(query, parameters={"node_address": address, "label": label})
        except Exception as e:
            print("Query failed:", e)
        finally:
            if session is not None:
                session.close()
        return response
# 
def init_db(uri, user, password):
    global conn
    conn = Neo4jConnection(uri, user, password)
# 
def get_degree(db_name, address):
    # Execute a Cypher query specifying the database name
    query_degree = """
    MATCH (a:account {address: $node_address})
    RETURN a.address AS address, size([(a)<--() | 1]) AS in_degree, size([(a)-->() | 1]) AS out_degree
    """

    parameters = {"node_address": address}
    query_result = conn.query(query_degree, parameters=parameters, db=db_name)
    if query_result:
        in_degree, out_degree = query_result[0]['in_degree'], query_result[0]['out_degree']
        print(f"Address: {address}, Indegree: {in_degree},  Outdegree: {out_degree}")
        return in_degree, out_degree
    else:
        return None, None
# 
def get_neighbors(db_name, address, limit):
    query_neighbors = """
    MATCH (ac:account {address: $node_address}) -[:input|output]-(:transaction)-[:input|output]-(an:account)
    WHERE ac <> an
    RETURN DISTINCT an.address AS nb_address
    LIMIT $limit
    """

    parameters = {"node_address": address, "limit": limit}
    query_result = conn.query(query_neighbors, parameters=parameters, db=db_name)
    nb_list = []
    for record in query_result:
        nb_list.append(record['nb_address'])
    return nb_list
#
def get_address_by_degree(db_name, upper_bound, lower_bound):
    query_address_by_degree = """
    MATCH (a:account)
    WITH a.address AS address, size([(a)<--() | 1]) AS in_degree, size([(a)-->() | 1]) AS out_degree
    WHERE (in_degree + out_degree) <= $upper_bound AND (in_degree + out_degree) >= $lower_bound
    RETURN address, in_degree, out_degree
    """

    parameters = {"upper_bound": upper_bound, "lower_bound": lower_bound}
    query_result = conn.query(query_address_by_degree, parameters=parameters, db=db_name)
    address_list = {}
    for record in query_result:
        address_list[record['address']] = (record['in_degree'], record['out_degree'])
    return address_list
# Close the connection
def close_db():
    conn.close()

if __name__ == '__main__':
    init_db("bolt://192.168.200.83:7687/", "reader", "P@ssw0rd")
    indegree, outdegree = get_degree(db_name='bitcoin', address='bc1q4c8n5t00jmj8temxdgcc3t32nkg2wjwz24lywv')
    print(indegree, outdegree)
    nb_list = get_neighbors(db_name='bitcoin', address='bc1q4c8n5t00jmj8temxdgcc3t32nkg2wjwz24lywv', limit=5)
    utils.saveJson('./nb_list.json', nb_list)
    close_db()
