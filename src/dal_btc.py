from neo4j import GraphDatabase
import utils

class Neo4jConnection:
    
    def __init__(self, uri, user, password):
        self.__uri = uri
        self.__user = user
        self.__password = password
        self.__driver = None
        try:
            self.__driver = GraphDatabase.driver(self.__uri, auth=(self.__user, self.__password))
        except Exception as e:
            print("Failed to create the driver:", e)
        
    def close(self):
        if self.__driver is not None:
            self.__driver.close()
        
    def query(self, query, parameters=None, db=None):
        session = None
        response = None
        try:
            # Specify the database name in the session method
            session = self.__driver.session(database=db) if db is not None else self.__driver.session() 
            response = list(session.run(query, parameters))
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