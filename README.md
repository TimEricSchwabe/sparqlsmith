# SPARQLsmith

A Python library for crafting, parsing, editing and analyzing SPARQL queries programmatically. .

## Installation

You can install the package via pip:

```bash
pip install sparqlsmith
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

```


## Features

- Craft SPARQL queries with precision and elegance
-  Support for:
  - Basic Graph Patterns (BGP)
  - UNION operations
  - OPTIONAL patterns
  - Filters
  - Subqueries
  - ORDER BY clauses
- query isomorphism checking
- Get query characteristics
- query string generation from query object


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