<p align="center">
  <img src="logo.png" alt="SPARQLsmith Logo" width="300"/>
</p>

# SPARQLsmith

[![Tests](https://github.com/TimEricSchwabe/sparqlsmith/workflows/Tests/badge.svg)](https://github.com/TimEricSchwabe/sparqlsmith/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A Python library for crafting, parsing, editing and analyzing SPARQL queries programmatically.

## ⚠️ Disclaimer: Early Alpha Stage

**Please note**: SPARQLSmith is currently in early alpha stage. There might be bugs, incomplete features, and API changes in future releases.

**SPARQL 1.1 Support Limitations**: Currently, SPARQLSmith only supports a subset of SPARQL 1.1 features focused primarily on SELECT queries. The following features are **not yet implemented**:

- Logical operators (&&, ||) in FILTER expressions
- BIND expressions
- Property paths
- VALUES clauses
- CONSTRUCT, ASK, and DESCRIBE query forms
- Named graphs (FROM, FROM NAMED)
- SERVICE for federated queries
- Sub-queries (not supported in parser)
- OFFSET and LIMIT clauses (partially supported)
- Support for Turtle syntax in queries

We're actively working on expanding the supported feature set. Contributions are welcome!

## Installation

You can install the package directly from GitHub:

```bash
pip install git+https://github.com/TimEricSchwabe/sparqlsmith.git
```

## Quick Start

### Building Queries programmatically

```python
from sparqlsmith import SPARQLQuery, BGP, TriplePattern, UnionOperator, Filter

# Create a query that finds people who are either authors of books or editors of journals
# and whose names start with 'A'

# Authors of books pattern
authors_pattern = BGP([
    TriplePattern('?person', '<http://example.org/isAuthorOf>', '?book'),
    TriplePattern('?book', '<http://example.org/type>', '<http://example.org/Book>')
])

# Editors of journals pattern
editors_pattern = BGP([
    TriplePattern('?person', '<http://example.org/isEditorOf>', '?journal'),
    TriplePattern('?journal', '<http://example.org/type>', '<http://example.org/Journal>')
])

# Combine with UNION
union = UnionOperator(left=authors_pattern, right=editors_pattern)

# Name pattern with filter directly associated with the BGP
name_bgp = BGP(
    triples=[TriplePattern('?person', '<http://example.org/name>', '?name')],
    filters=[Filter("REGEX(STR(?name), '^a', 'i')")]
)

# Create the complete query
query = SPARQLQuery(
    projection_variables=['?person', '?name'],
    where_clause=[name_bgp, union]
)

# Generate SPARQL query string
sparql_query = query.to_query_string()
print(sparql_query)
```

**Output:**
```
SPARQLQuery:
  Projection: ?person, ?name
  Where Clause:
    BGP:
      Triple: ?person <http://example.org/name> ?name
      Filters:
        REGEX(STR(?name), '^A', 'i')
    UNION:
      Left:
        BGP:
          Triple: ?person <http://example.org/isAuthorOf> ?book
          Triple: ?book <http://example.org/type> <http://example.org/Book>
      Right:
        BGP:
          Triple: ?person <http://example.org/isEditorOf> ?journal
          Triple: ?journal <http://example.org/type> <http://example.org/Journal>
----------------------------------------------------------------------------------------------------
SELECT ?person ?name
WHERE {
  ?person <http://example.org/name> ?name .
  FILTER(REGEX(STR(?name), '^A', 'i'))
  {
    ?person <http://example.org/isAuthorOf> ?book .
    ?book <http://example.org/type> <http://example.org/Book> .
  } UNION {
    ?person <http://example.org/isEditorOf> ?journal .
    ?journal <http://example.org/type> <http://example.org/Journal> .
  }
}
```

### Adding and Removing Elements

SPARQLsmith includes a simple API for adding and removing components from queries:

```python
from sparqlsmith import SPARQLQuery, BGP, TriplePattern, UnionOperator, Filter

# Start with an empty query
query = SPARQLQuery(projection_variables=["?person", "?name"])

# Create and add a BGP for people
people_bgp = BGP()
people_bgp.add(TriplePattern("?person", "<http://example.org/type>", "<http://example.org/Person>")) # add a triple pattern to the BGP
people_bgp.add(TriplePattern("?person", "<http://example.org/name>", "?name"))
people_bgp.add(Filter("?person != <http://example.org/excluded>")) # add filters to the BGP
query.add(people_bgp) # add the BGP to the query

# Adding a UNION operator
author_bgp = BGP()
author_bgp.add(("?person", "<http://example.org/isAuthor>", "?true"))

editor_bgp = BGP()
editor_bgp.add(("?person", "<http://example.org/isEditor>", "?true"))

union = UnionOperator(left=author_bgp, right=editor_bgp)
query.add(union)

print("COMPLETE QUERY:")
print(query.to_query_string())


print("\nREMOVING A TRIPLE FROM THE PEOPLE BGP:")
# Removing the first triple of the people BGP
query.where_clause[0].triples[0].remove() # alternatively, you can also access the underlying BGP directly:people_bgp.triples[0].remove()
print(query.to_query_string())

print("\nREMOVING THE UNION:")
query.where_clause[1].remove()
print(query.to_query_string())
```

**Output:**
```
from sparqlsmith import SPARQLQuery, BGP, TriplePattern, UnionOperator, Filter

# Start with an empty query
query = SPARQLQuery(projection_variables=["?person", "?name"])

# Create and add a BGP for people
people_bgp = BGP()
people_bgp.add(TriplePattern("?person", "<http://example.org/type>", "<http://example.org/Person>")) # add a triple pattern to the BGP
people_bgp.add(TriplePattern("?person", "<http://example.org/name>", "?name"))
people_bgp.add(Filter("?person != <http://example.org/excluded>")) # add filters to the BGP
query.add(people_bgp) # add the BGP to the query

# Adding a UNION operator
author_bgp = BGP()
author_bgp.add(("?person", "<http://example.org/isAuthor>", "?true"))

editor_bgp = BGP()
editor_bgp.add(("?person", "<http://example.org/isEditor>", "?true"))

union = UnionOperator(left=author_bgp, right=editor_bgp)
query.add(union)

print("COMPLETE QUERY:")
print(query.to_query_string())


print("\nREMOVING A TRIPLE FROM THE PEOPLE BGP:")
# Removing the first triple of the people BGP
query.where_clause[0].triples[0].remove() # alternatively, you can also access the underlying BGP directly:people_bgp.triples[0].remove()
print(query.to_query_string())

print("\nREMOVING THE UNION:")
query.where_clause[1].remove()
print(query.to_query_string())
```


## Query Isomorphism

SPARQLsmith provides a query isomorphism checking feature that determines if two SPARQL queries have the same structure, even with different variable names.

### Mathematical Definition

Formally, two SPARQL where clauses $P_1$ and $P_2$ are isomorphic if there exists a bijective function $f$ between the variables in $P_1$ and $P_2$ such that:

1. If we replace each variable $v$ in $P_1$ with $f(v)$, we obtain a pattern that is structurally identical to $P_2$.
2. The structure and operators (UNION, OPTIONAL, etc.) are preserved through this mapping.

### Algorithm Implementation

The current implementation uses a backtracking approach to find a consistent variable mapping:

1. For Basic Graph Patterns (BGPs):
   - For each triple pattern in the first BGP, we attempt to match it with an unused triple pattern in the second BGP.
   - The variable mappings must be consistent across all matchings.

2. For UNION operators:
   - We check if either (left₁ ↔ left₂ and right₁ ↔ right₂) or (left₁ ↔ right₂ and right₁ ↔ left₂) are isomorphic.
   - This accounts for the commutative nature of UNION.

3. For OPTIONAL patterns:
   - We verify if the contained graph patterns are isomorphic.

### Current Limitations

The current implementation:
- Focuses on structural isomorphism of patterns, not full semantic equivalence
- Does not consider query solution modifiers (ORDER BY, LIMIT, etc.) in the isomorphism check
- Does not fully analyze FILTER expressions (only checks if they exist in the same structural positions)
- Does not account for differences in projection variables

### Example

```python
# These queries are isomorphic despite different variable names and UNION ordering
from sparqlsmith.parser import SPARQLParser
from sparqlsmith.query import SPARQLQuery, BGP, TriplePattern, UnionOperator

query1 = SPARQLQuery(
    projection_variables=['?s'],
    prefixes={'ex': '<http://example.com>'},
    where_clause=UnionOperator(
        left=BGP([TriplePattern('?s', 'ex:p', '?o1')]),
        right=BGP([TriplePattern('?s', 'ex:q', '?o2')])
    )
)

query2 = SPARQLQuery(
    projection_variables=['?subject'],
    prefixes={'ex': '<http://example.com>'},
    where_clause=UnionOperator(
        left=BGP([TriplePattern('?subject', 'ex:q', '?object2')]),
        right=BGP([TriplePattern('?subject', 'ex:p', '?object1')])
    )
)

# Returns True because the patterns are structurally equivalent
print(query1.is_isomorphic(query2))


exit()
```

**Output:**
```
True
```

### Instantiating variables in a query
```python
bgp = BGP([
    TriplePattern('?s', '?p1', '?o1'),
    TriplePattern('?s', '?p2', '?o2'),
    TriplePattern('?o1', '?p3', '?o3'),
])

query = SPARQLQuery(
    projection_variables=['?s', '?o1', '?o3'],
    where_clause=bgp
)
mapping = {
    'p1': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type',
    'p2': 'http://example.org/predicate2',
    'o2': 'http://example.org/object2',
}

# Create a copy of the query and instantiate it
instantiated_query = query.instantiate(mapping)
print(instantiated_query.to_query_string())
```

**Output:**
```
SELECT ?s ?o1 ?o3
WHERE {
  ?s <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> ?o1 .
  ?s <http://example.org/predicate2> <http://example.org/object2> .
  ?o1 ?p3 ?o3 .
}
```

Analyzing Query Features

```python
from sparqlsmith import SPARQLQuery, BGP, TriplePattern, UnionOperator, Filter

bgp = BGP([
    TriplePattern('?s', '?p1', '?o1'),
    TriplePattern('?s', '?p2', '?o2'),
    TriplePattern('?s', '?p3', '?o3'),
])

query = SPARQLQuery(
    projection_variables=['?s', '?o1', '?o3'],
    where_clause=bgp
)
print('Number of triple patterns:', query.n_triple_patterns) # print the number of triple patterns in the query
print('Number of BGPs:', query.count_bgps()) # print the number of bgps in the query
print('Variables:', query.get_all_variables()) # print all variables in the query 
print('Projection variables:', query.projection_variables) # print all variables that are projected
print('BGP shape:', bgp.shape()) # print the shape of the BGP in the query
```

**Output:**
```
Number of triple patterns: 3
Number of BGPs: 1
Variables: {'?o1', '?o3', '?p3', '?o2', '?p2', '?s', '?p1'}
Projection variables: ['?s', '?o1', '?o3']
BGP shape: Star
```

Parsing SPARQL Queries

```python
from sparqlsmith import SPARQLParser

# Create a parser instance
parser = SPARQLParser()

# Example SPARQL query string
query_str = """
    SELECT ?person ?name 
    WHERE { 
        ?person :name ?name .
        ?person :age ?age .
        FILTER(?age > 25)
    }
"""


# Parse the query string to a SPARQLQuery object
query = parser.parse_to_query(query_str)
# print back the query string from the Query object
print(query.to_query_string())
```

**Output:**
```sparql
SELECT ?person ?name
WHERE {
  ?person :name ?name .
  ?person :age ?age .
  FILTER(?age > 25)
}
```

## Features

Support for:
  - Basic Graph Patterns (BGP)
  - UNION operations
  - OPTIONAL patterns
  - Filters
  - ORDER BY clauses
  - GROUP BY clauses
  - Aggregation functions (COUNT, SUM, MIN, MAX, AVG)
- Query isomorphism checking
- Query characteristics
- Query string generation from query object

## Development

To set up the development environment:

```bash
# Clone the repository
git clone https://github.com/yourusername/sparqlsmith.git
cd sparqlsmith

# Install development dependencies
pip install -e ".[dev]"
```

### Running Tests

```bash
pytest tests/
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Examples

### Using Aggregation Functions

```python
from sparqlsmith import SPARQLQuery, BGP, TriplePattern, AggregationExpression, GroupBy

# Create a query with aggregation functions
bgp = BGP([
    TriplePattern('?person', ':age', '?age'),
    TriplePattern('?person', ':salary', '?salary')
])

# Create aggregation expressions
count_agg = AggregationExpression(
    function='COUNT',
    variable='?person',
    alias='?count',
    distinct=True
)

sum_agg = AggregationExpression(
    function='SUM',
    variable='?salary',
    alias='?totalSalary'
)

query = SPARQLQuery(
    projection_variables=['?age'],
    where_clause=bgp,
    group_by=GroupBy(variables=['?age']),
    aggregations=[count_agg, sum_agg]
)

# Generate SPARQL query string
sparql_query = query.to_query_string()
print(sparql_query)
```

**Output:**
```sparql
SELECT ?age (COUNT(DISTINCT ?person) AS ?count) (SUM(?salary) AS ?totalSalary)
WHERE {
  ?person :age ?age .
  ?person :salary ?salary .
}
GROUP BY ?age
``` 