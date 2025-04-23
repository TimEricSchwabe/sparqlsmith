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
- Sub-queries
- OFFSET and LIMIT clauses (partially supported)
- Support for Turtle syntax in queries

We're actively working on expanding the supported feature set. Contributions are welcome!

## Installation

You can install the package directly from GitHub:

```bash
pip install git+https://github.com/TimEricSchwabe/sparqlsmith.git
```

## Quick Start

Building Queries programmatically

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

# Add name pattern and filter
query = SPARQLQuery(
    projection_variables=['?person', '?name'],
    where_clause=[
        BGP([TriplePattern('?person', '<http://example.org/name>', '?name')]),
        union
    ],
    filters=[Filter("REGEX(STR(?name), '^A', 'i')")]
)

# Generate SPARQL query string
sparql_query = query.to_query_string()
print(sparql_query)
```

Checking if queries are isomorphic
```python
query1 = SPARQLQuery(
    projection_variables=['*'],
    where_clause=UnionOperator(
        left=BGP([TriplePattern('?s', ':type', ':Person')]),
        right=BGP([TriplePattern('?s', ':type', ':Organization')])
    )
)

query2 = SPARQLQuery(
    projection_variables=['*'],
    where_clause=UnionOperator(
        left=BGP([TriplePattern('?x', ':type', ':Organization')]),
        right=BGP([TriplePattern('?x', ':type', ':Person')])
    )
)

print(query1.is_isomorphic(query2)) # True
```

Instantiating variables in a query
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
query.instantiate(mapping)
```

Analyzing Query Features

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

print(query.n_triple_patterns) # print the number of triple patterns in the query
print(query.count_bgps()) # print the number of bgps in the query
print(query.get_all_variables()) # print all variables in the query 
print(query1.projection_variables) # print all variables that are projected

# Print the structure of the query
print(query) 
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
```

## Features

-  Support for:
  - Basic Graph Patterns (BGP)
  - UNION operations
  - OPTIONAL patterns
  - Filters
  - Subqueries
  - ORDER BY clauses
  - GROUP BY clauses
  - Aggregation functions (COUNT, SUM, MIN, MAX, AVG)
- Query isomorphism checking
- Get query characteristics
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
# Output:
# SELECT ?age (COUNT(DISTINCT ?person) AS ?count) (SUM(?salary) AS ?totalSalary)
# WHERE {
#   ?person :age ?age .
#   ?person :salary ?salary .
# }
# GROUP BY ?age 