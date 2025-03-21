from sparqlsmith.query import BGP, TriplePattern, SPARQLQuery

'''
This script shows how variables in a query can be instantiated with a mapping.
It also shows how to analyze queries for different characteristics.
'''

def main():
    # Define a query with multiple triple patterns
    bgp1 = BGP([
        TriplePattern('?s', '?p1', '?o1'),
        TriplePattern('?s', '?p2', '?o2'),
        TriplePattern('?o1', '?p3', '?o3'),
    ])
    
    query1 = SPARQLQuery(
        projection_variables=['?s', '?o1', '?o3'],
        where_clause=bgp1
    )

    print("Original Query:")
    print(query1.to_query_string())
    print("\nQuery Analysis:")
    print(f"Number of triple patterns: {query1.n_triple_patterns}")
    print(f"Number of BGPs: {query1.count_bgps()}")
    print(f"All variables: {query1.get_all_variables()}")
    print(f"Projection variables: {query1.projection_variables}")

    # Instantiate query with a mapping
    mapping = {
        'p1': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type',
        'p2': 'http://example.org/predicate2',
        'o2': 'http://example.org/object2',
    }

    # Create a copy of the query and instantiate it
    instantiated_query = query1.copy()
    instantiated_query.instantiate(mapping)

    print("\nInstantiated Query:")
    print(instantiated_query.to_query_string())
    print("\nInstantiated Query Analysis:")
    print(f"Number of triple patterns: {instantiated_query.n_triple_patterns}")
    print(f"Number of BGPs: {instantiated_query.count_bgps()}")
    print(f"All variables: {instantiated_query.get_all_variables()}")
    print(f"Projection variables: {instantiated_query.projection_variables}")

    # Example of a more complex query with OPTIONAL and UNION
    bgp2 = BGP([
        TriplePattern('?x', '?p4', '?y'),
        TriplePattern('?y', '?p5', '?z'),
    ])

    bgp3 = BGP([
        TriplePattern('?x', '?p6', '?w'),
    ])

    from sparqlsmith.query import UnionOperator

    union_pattern = UnionOperator(bgp1, bgp3)

    complex_query = SPARQLQuery(
        projection_variables=['?s', '?x', '?y'],
        where_clause=union_pattern
    )

    print("Query:")
    print(complex_query.to_query_string())
    print("Query Analysis:")
    print(f"Number of triple patterns: {complex_query.n_triple_patterns}")
    print(f"Number of BGPs: {complex_query.count_bgps()}")
    print(f"All variables: {complex_query.get_all_variables()}")
    print(f"Projection variables: {complex_query.projection_variables}")

if __name__ == "__main__":
    main() 