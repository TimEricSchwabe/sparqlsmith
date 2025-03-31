from sparqlsmith.query import SPARQLQuery, BGP, TriplePattern, Filter
from sparqlsmith.filter_ast import (
    Variable, Literal, ValueType, 
    and_, or_, not_, equals, not_equals, less_than, greater_than,
    regex, str_func, exists, in_list, parse_filter
)

# Create a basic graph pattern
bgp = BGP()
bgp.add_triple_pattern("?person", "rdf:type", "foaf:Person")
bgp.add_triple_pattern("?person", "foaf:name", "?name")
bgp.add_triple_pattern("?person", "foaf:age", "?age")

# Example 1: Simple comparison filter
# Filter: ?age > 25
age_filter = Filter(greater_than(
    Variable("?age"),
    Literal(25, ValueType.NUMBER)
))

# Example 2: Complex boolean expression
# Filter: ?age > 25 && (?name = "John" || ?name = "Jane")
complex_filter = Filter(and_(
    greater_than(Variable("?age"), Literal(25, ValueType.NUMBER)),
    or_(
        equals(Variable("?name"), Literal("John", ValueType.STRING)),
        equals(Variable("?name"), Literal("Jane", ValueType.STRING))
    )
))

# Example 3: Function call - REGEX
# Filter: REGEX(STR(?name), "^A", "i")
regex_filter = Filter(regex(
    str_func(Variable("?name")),
    Literal("^A", ValueType.STRING),
    Literal("i", ValueType.STRING)
))

# Example 4: Negation
# Filter: !(?age < 18)
negation_filter = Filter(not_(
    less_than(Variable("?age"), Literal(18, ValueType.NUMBER))
))

# Example 5: IN operator
# Filter: ?name IN ("Alice", "Bob", "Charlie")
in_filter = Filter(in_list(
    Variable("?name"),
    Literal("Alice", ValueType.STRING),
    Literal("Bob", ValueType.STRING),
    Literal("Charlie", ValueType.STRING)
))

# Example 6: Legacy string filter (for backward compatibility)
legacy_filter = Filter("?age > 25")

# Create queries with each filter
query1 = SPARQLQuery(
    projection_variables=["?person", "?name", "?age"],
    where_clause=bgp,
    filters=[age_filter]
)

query2 = SPARQLQuery(
    projection_variables=["?person", "?name", "?age"],
    where_clause=bgp,
    filters=[complex_filter]
)

query3 = SPARQLQuery(
    projection_variables=["?person", "?name"],
    where_clause=bgp,
    filters=[regex_filter]
)

query4 = SPARQLQuery(
    projection_variables=["?person", "?name", "?age"],
    where_clause=bgp,
    filters=[negation_filter]
)

query5 = SPARQLQuery(
    projection_variables=["?person", "?name", "?age"],
    where_clause=bgp,
    filters=[in_filter]
)

query6 = SPARQLQuery(
    projection_variables=["?person", "?name", "?age"],
    where_clause=bgp,
    filters=[legacy_filter]
)

# Example 7: Using the parser to convert a string filter to an AST
try:
    # Parse a simple comparison
    parsed_filter1 = Filter(parse_filter("?age > 25"))
    
    # Parse a more complex expression
    parsed_filter2 = Filter(parse_filter("?age > 25 && (?name = \"John\" || ?name = \"Jane\")"))
    
    # Parse a REGEX function call
    parsed_filter3 = Filter(parse_filter("REGEX(STR(?name), \"^A\", \"i\")"))
    
    # Create queries with the parsed filters
    query7 = SPARQLQuery(
        projection_variables=["?person", "?name", "?age"],
        where_clause=bgp,
        filters=[parsed_filter1]
    )
    
    query8 = SPARQLQuery(
        projection_variables=["?person", "?name", "?age"],
        where_clause=bgp,
        filters=[parsed_filter2]
    )
    
    query9 = SPARQLQuery(
        projection_variables=["?person", "?name"],
        where_clause=bgp,
        filters=[parsed_filter3]
    )
    
    print("\nExample 7: Parsed simple comparison filter")
    print(query7.to_query_string())
    
    print("\nExample 8: Parsed complex boolean expression")
    print(query8.to_query_string())
    
    print("\nExample 9: Parsed REGEX function")
    print(query9.to_query_string())
except ValueError as e:
    print(f"\nParser error: {e}")
    print("Note: The parser is a basic implementation and doesn't handle all SPARQL filter syntax.")

# Print all queries
print("Example 1: Simple comparison filter")
print(query1.to_query_string())
print("\nExample 2: Complex boolean expression")
print(query2.to_query_string())
print("\nExample 3: REGEX function")
print(query3.to_query_string())
print("\nExample 4: Negation")
print(query4.to_query_string())
print("\nExample 5: IN operator")
print(query5.to_query_string())
print("\nExample 6: Legacy string filter")
print(query6.to_query_string()) 