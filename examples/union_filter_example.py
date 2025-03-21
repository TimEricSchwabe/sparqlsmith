from sparqlsmith import (
    SPARQLQuery,
    BGP,
    TriplePattern,
    UnionOperator,
    Filter
)

def main():
    # Create the left part of the UNION
    # This will match people who are authors of books
    left_bgp = BGP([
        TriplePattern('?person', '<http://example.org/isAuthorOf>', '?book'),
        TriplePattern('?book', '<http://example.org/type>', '<http://example.org/Book>')
    ])

    # Create the right part of the UNION
    # This will match people who are editors of journals
    right_bgp = BGP([
        TriplePattern('?person', '<http://example.org/isEditorOf>', '?journal'),
        TriplePattern('?journal', '<http://example.org/type>', '<http://example.org/Journal>')
    ])

    # Combine them with a UNION operator
    union = UnionOperator(left=left_bgp, right=right_bgp)

    # Create a filter to only include people whose names start with 'A'
    filter_expr = Filter("REGEX(STR(?name), '^A', 'i')")

    # Create the main query
    # We'll add a triple pattern to get the person's name
    name_pattern = BGP([
        TriplePattern('?person', '<http://example.org/name>', '?name')
    ])

    # Create the full query with both patterns and the filter
    query = SPARQLQuery(
        projection_variables=['?person', '?name'],
        where_clause=[name_pattern, union],
        filters=[filter_expr]
    )

    # Generate and print the SPARQL query string
    print("Generated SPARQL Query:")
    print("----------------------")
    print(query.to_query_string())


if __name__ == '__main__':
    main() 