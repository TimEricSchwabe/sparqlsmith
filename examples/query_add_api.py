#!/usr/bin/env python3

"""
SPARQLsmith Add API Examples

This script demonstrates how to use the add() API in SPARQLsmith
to build SPARQL queries programmatically.
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

# 1. Create an empty query
query = SPARQLQuery()

# 2. Adding a basic graph pattern (BGP) using different methods
bgp = BGP()

# 2.1 Add a triple pattern using the new add() method with tuple
bgp.add(("?person", "<http://example.org/type>", "<http://example.org/Person>"))

# 2.2 Add a triple pattern using the new add() method with a TriplePattern object
name_triple = TriplePattern("?person", "<http://example.org/name>", "?name")
bgp.add(name_triple)

# 2.3 Add a filter using the new add() method with a string
bgp.add("REGEX(?name, '^A', 'i')")

# 2.4 Add a filter using the new add() method with a Filter object
age_filter = Filter("?age > 25")
bgp.add(age_filter)

# 2.5 Add the BGP to the query using the query.add() method
query.add(bgp)
print_query_status(query, "AFTER ADDING BGP WITH TRIPLES AND FILTERS")

# 3. Create and add a UNION pattern
# 3.1 Create the left and right parts of the UNION
publication_bgp = BGP()
publication_bgp.add(("?person", "<http://example.org/wrote>", "?publication"))
publication_bgp.add(("?publication", "<http://example.org/title>", "?title"))

organization_bgp = BGP()
organization_bgp.add(("?person", "<http://example.org/worksAt>", "?organization"))
organization_bgp.add(("?organization", "<http://example.org/name>", "?orgName"))

# 3.2 Create the UNION operator with left and right BGPs in the constructor
union_op = UnionOperator(left=publication_bgp, right=organization_bgp)


# 3.3 Add the UNION to the query
query.add(union_op)
print_query_status(query, "AFTER ADDING UNION OPERATOR")

# 4. Create and add an OPTIONAL pattern
# 4.1 Create a BGP for the OPTIONAL part
email_bgp = BGP()
email_bgp.add(("?person", "<http://example.org/email>", "?email"))

# 4.2 Create an OPTIONAL operator with the BGP in the constructor
optional_op = OptionalOperator(bgp=email_bgp)

# 4.3 Add the OPTIONAL to the query
query.add(optional_op)
print_query_status(query, "AFTER ADDING OPTIONAL PATTERN")

# 5. Add a top-level filter to the query
query.add(Filter("?age < 65"))
print_query_status(query, "AFTER ADDING TOP-LEVEL FILTER")

# 6. Add GROUP BY clause
query.add_group_by("?person")
print_query_status(query, "AFTER ADDING GROUP BY")

# 7. Add an aggregation
agg = AggregationExpression(
    function="COUNT",
    variable="?publication",
    alias="?pubCount",
    distinct=True
)
query.add_aggregation(agg)
print_query_status(query, "AFTER ADDING AGGREGATION")

# 8. Add HAVING clause
query.add_having("COUNT(?publication) > 3")
print_query_status(query, "AFTER ADDING HAVING CLAUSE")

# 9. Add ORDER BY clause
query.add_order_by(["?pubCount", "?name"], [False, True])  # descending, ascending
print_query_status(query, "AFTER ADDING ORDER BY")

# 10. Set LIMIT and OFFSET
query.set_limit(10).set_offset(20)
print_query_status(query, "AFTER ADDING LIMIT AND OFFSET")

# 11. Set DISTINCT flag
query.set_distinct(True)
print_query_status(query, "AFTER SETTING DISTINCT FLAG")

# 12. Demonstrate the new combined GROUP BY and aggregation API
another_query = SPARQLQuery()
bgp = BGP()
bgp.add(("?student", "<http://example.org/attends>", "?class"))
bgp.add(("?student", "<http://example.org/score>", "?score"))
another_query.add(bgp)

# Create aggregations
count_agg = AggregationExpression(
    function="COUNT",
    variable="?student",
    alias="?studentCount", 
    distinct=True
)

avg_agg = AggregationExpression(
    function="AVG",
    variable="?score",
    alias="?avgScore"
)

# Add GROUP BY and aggregations in one call
another_query.add_group_by("?class", aggregations=[count_agg, avg_agg])

# Set projection variables
another_query.projection_variables = ["?class", "?studentCount", "?avgScore"]

print_query_status(another_query, "QUERY WITH COMBINED GROUP BY AND AGGREGATIONS")

# 13. Using a group graph pattern
group = GroupGraphPattern(None)
inner_bgp = BGP()
inner_bgp.add(("?s", "?p", "?o"))
group.add(inner_bgp)
group.add("?p != <http://example.org/exclude>")

query_with_group = SPARQLQuery()
query_with_group.add(group)
print_query_status(query_with_group, "QUERY WITH GROUP GRAPH PATTERN")

print("\nAll add examples completed successfully.") 