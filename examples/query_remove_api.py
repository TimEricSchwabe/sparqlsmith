#!/usr/bin/env python3

"""
SPARQLsmith Removal Examples

This script demonstrates how to use the removal API in SPARQLsmith
to manipulate SPARQL queries by removing components.
"""

from sparqlsmith.query import (
    SPARQLQuery, BGP, TriplePattern, UnionOperator, 
    OptionalOperator, Filter, OrderBy, GroupBy, 
    Having, AggregationExpression, GroupGraphPattern
)

def print_query_status(query, message):
    """Helper function to print query status with message"""
    print("\n" + "="*80)
    print(f"{message}")
    print("="*80)
    print(query.to_query_string())
    print("-"*80)

# 1. Create a complex query with multiple components
print("Creating a complex SPARQL query with various components...")

# Creating person BGP with two triple patterns and a filter
person_bgp = BGP([
    TriplePattern("?person", "<http://example.org/type>", "<http://example.org/Person>"),
    TriplePattern("?person", "<http://example.org/name>", "?name")
], [
    Filter("REGEX(?name, '^A', 'i')")
])

# Creating publication BGP
publication_bgp = BGP([
    TriplePattern("?person", "<http://example.org/wrote>", "?publication"),
    TriplePattern("?publication", "<http://example.org/title>", "?title"),
    TriplePattern("?publication", "<http://example.org/year>", "?year")
])

# Creating organization BGP
organization_bgp = BGP([
    TriplePattern("?person", "<http://example.org/worksAt>", "?organization"),
    TriplePattern("?organization", "<http://example.org/name>", "?orgName")
])

# Create a union of publication and organization
union_op = UnionOperator(
    left=publication_bgp,
    right=organization_bgp
)

# Create an optional pattern for emails
email_bgp = BGP([
    TriplePattern("?person", "<http://example.org/email>", "?email")
])
optional_op = OptionalOperator(bgp=email_bgp)

# Create a group by clause
group_by = GroupBy(variables=["?person"])

# Create aggregation expressions
count_agg = AggregationExpression(
    function="COUNT",
    variable="?publication",
    alias="?pubCount",
    distinct=True
)

# Create having clause
having = Having(expression="COUNT(?publication) > 5")

# Create order by clause
order_by = OrderBy(
    variables=["?pubCount", "?name"],
    ascending=[False, True]  # Descending for pubCount, ascending for name
)

# Create the complete query
query = SPARQLQuery(
    projection_variables=["?person"],
    where_clause=[person_bgp, union_op, optional_op],
    group_by=group_by,
    having=[having],
    order_by=order_by,
    aggregations=[count_agg],
    is_distinct=True
)

# Print the initial query
print_query_status(query, "INITIAL QUERY")

# 2. Demonstrate removing triple patterns
# Option 1: Access the BGP directly
#triple_to_remove = person_bgp.triples[1]  # The name triple
# Option 2: alternatively access the BGP from the query object
triple_to_remove = query.where_clause[0].triples[1]
triple_to_remove.remove()
print_query_status(query, "AFTER REMOVING '?person <http://example.org/name> ?name' TRIPLE")

# 3. Demonstrate removing filters
filter_to_remove = query.where_clause[0].filters[0]  # The REGEX filter
filter_to_remove.remove()
print_query_status(query, "AFTER REMOVING FILTER")

# 4. Demonstrate removing optional pattern
# Option 1: Access the BGP directly
#optional_op.remove()
# Option 2: alternatively access the BGP from the query object
query.where_clause[2].remove()
print_query_status(query, "AFTER REMOVING OPTIONAL PATTERN")

# 5. Demonstrate removing from a union
query.where_clause[1].left.triples[1].remove()
print_query_status(query, "AFTER REMOVING '?publication <title> ?title' FROM UNION LEFT SIDE")

# 6. Demonstrate removing aggregation
query.aggregations[0].remove()
print_query_status(query, "AFTER REMOVING COUNT AGGREGATION")

# 7. Demonstrate removing HAVING clause
query.having[0].remove()
print_query_status(query, "AFTER REMOVING HAVING CLAUSE")

# 8. Demonstrate removing ORDER BY
query.order_by.remove()
print_query_status(query, "AFTER REMOVING ORDER BY")

# 9. Demonstrate removing GROUP BY
query.group_by.remove()
print_query_status(query, "AFTER REMOVING GROUP BY")

# 10. Demonstrate removing complete BGP
query.where_clause[0].remove()
print_query_status(query, "AFTER REMOVING PERSON BGP")

# 11. Demonstrate removing union operator
query.where_clause[0].remove()
print_query_status(query, "AFTER REMOVING UNION OPERATOR")

print("\nAll removal operations demonstrated successfully.") 