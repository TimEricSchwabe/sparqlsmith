from sparqlsmith import (
    SPARQLQuery,
    BGP,
    TriplePattern,
    UnionOperator,
    OptionalOperator
)

def demonstrate_simple_bgp_isomorphism():
    """
    Demonstrates isomorphism with simple Basic Graph Patterns (BGPs).
    These queries are isomorphic because they have the same structure
    with just different variable names.
    """
    # First query
    bgp1 = BGP([
        TriplePattern('?person', ':name', '?name'),
        TriplePattern('?person', ':age', '?age')
    ])
    query1 = SPARQLQuery(
        projection_variables=['?person', '?name', '?age'],
        where_clause=bgp1
    )

    # Second query - isomorphic to first but with different variable names
    bgp2 = BGP([
        TriplePattern('?x', ':name', '?n'),
        TriplePattern('?x', ':age', '?a')
    ])
    query2 = SPARQLQuery(
        projection_variables=['?x', '?n', '?a'],
        where_clause=bgp2
    )

    print("Simple BGP Isomorphism Example:")
    print("Query 1:")
    print(query1.to_query_string())
    print("\nQuery 2:")
    print(query2.to_query_string())
    print("\nAre these queries isomorphic?", query1.is_isomorphic(query2))
    print("-" * 50)

def demonstrate_union_isomorphism():
    """
    Demonstrates isomorphism with UNION patterns.
    These queries are isomorphic because they have the same structure
    even though the UNION parts are in different order.
    """
    # First query
    query1 = SPARQLQuery(
        projection_variables=['*'],
        where_clause=UnionOperator(
            left=BGP([TriplePattern('?s', ':type', ':Person')]),
            right=BGP([TriplePattern('?s', ':type', ':Organization')])
        )
    )

    # Second query - isomorphic to first but with UNION parts swapped
    query2 = SPARQLQuery(
        projection_variables=['*'],
        where_clause=UnionOperator(
            left=BGP([TriplePattern('?x', ':type', ':Organization')]),
            right=BGP([TriplePattern('?x', ':type', ':Person')])
        )
    )

    print("UNION Isomorphism Example:")
    print("Query 1:")
    print(query1.to_query_string())
    print("\nQuery 2:")
    print(query2.to_query_string())
    print("\nAre these queries isomorphic?", query1.is_isomorphic(query2))
    print("-" * 50)

def demonstrate_optional_isomorphism():
    """
    Demonstrates isomorphism with OPTIONAL patterns.
    These queries are isomorphic because they have the same structure
    with mandatory and optional patterns.
    """
    # First query
    main_bgp1 = BGP([TriplePattern('?person', ':name', '?name')])
    optional1 = OptionalOperator(
        bgp=BGP([TriplePattern('?person', ':email', '?email')])
    )
    query1 = SPARQLQuery(
        projection_variables=['?person', '?name', '?email'],
        where_clause=[main_bgp1, optional1]
    )

    # Second query - isomorphic to first but with different variable names
    main_bgp2 = BGP([TriplePattern('?p', ':name', '?n')])
    optional2 = OptionalOperator(
        bgp=BGP([TriplePattern('?p', ':email', '?e')])
    )
    query2 = SPARQLQuery(
        projection_variables=['?p', '?n', '?e'],
        where_clause=[main_bgp2, optional2]
    )

    print("OPTIONAL Isomorphism Example:")
    print("Query 1:")
    print(query1.to_query_string())
    print("\nQuery 2:")
    print(query2.to_query_string())
    print("\nAre these queries isomorphic?", query1.is_isomorphic(query2))
    print("-" * 50)

def demonstrate_non_isomorphic_queries():
    """
    Demonstrates examples of non-isomorphic queries to highlight
    the differences that make queries non-isomorphic.
    """
    # Query with two triple patterns
    query1 = SPARQLQuery(
        projection_variables=['?s', '?p', '?o'],
        where_clause=BGP([
            TriplePattern('?s', ':p', '?o'),
            TriplePattern('?s', ':q', '?o')
        ])
    )

    # Query with one triple pattern - not isomorphic
    query2 = SPARQLQuery(
        projection_variables=['?s', '?p', '?o'],
        where_clause=BGP([
            TriplePattern('?s', ':p', '?o')
        ])
    )

    print("Non-isomorphic Queries Example:")
    print("Query 1:")
    print(query1.to_query_string())
    print("\nQuery 2:")
    print(query2.to_query_string())
    print("\nAre these queries isomorphic?", query1.is_isomorphic(query2))
    print("-" * 50)

def main():
    print("SPARQL Query Isomorphism Examples")
    print("=================================\n")
    
    demonstrate_simple_bgp_isomorphism()
    demonstrate_union_isomorphism()
    demonstrate_optional_isomorphism()
    demonstrate_non_isomorphic_queries()

if __name__ == '__main__':
    main() 