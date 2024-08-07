from neo4j import GraphDatabase

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

    def __del__(self):
        if self.__driver is not None:
            self.__driver.close()
            # print("Driver closed")
    
    def get_degree(self, db_name, address):
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
            print("Query failed:", e)
        finally:
            if session is not None:
                session.close()
        return in_degree, out_degree
    
    def get_neighbors(self, db_name, address, limit):
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
            print("Query failed:", e)
        finally:
            if session is not None:
                session.close()
        return neighbors
    
    def get_address_by_degree(self, db_name, upper_bound, lower_bound):
        query = """
        MATCH (a:account)
        WITH a.address AS address, size([(a)<--() | 1]) AS in_degree, size([(a)-->() | 1]) AS out_degree
        WHERE (in_degree + out_degree) <= $upper_bound AND (in_degree + out_degree) >= $lower_bound
        RETURN address, in_degree, out_degree
        """
    
        session = None
        response = None
        address_list = {}
        try:
            session = self.__driver.session(database=db_name)
            response = list(session.run(query, parameters={"upper_bound": upper_bound, "lower_bound": lower_bound}))
            for record in response:
                address_list[record['address']] = (record['in_degree'], record['out_degree'])
        except Exception as e:
            print("Query failed:", e)
        finally:
            if session is not None:
                session.close()
        return address_list

if __name__ == '__main__':
    conn = Neo4jConnection("bolt://192.168.200.83:7687/", "reader", "P@ssw0rd")
    indegree, outdegree = conn.get_degree(db_name='bitcoin', address='bc1q4c8n5t00jmj8temxdgcc3t32nkg2wjwz24lywv')
    print(indegree, outdegree)
    neighbors = conn.get_neighbors(db_name='bitcoin', address='bc1q4c8n5t00jmj8temxdgcc3t32nkg2wjwz24lywv', limit=10)
    print(neighbors)
    address_list = conn.get_address_by_degree(db_name='bitcoin3', upper_bound=float('inf'), lower_bound=10000)
    print(address_list)