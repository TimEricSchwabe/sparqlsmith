# SPARQLsmith

A Python library for crafting, parsing, editing and analyzing SPARQL queries programmatically.

## Installation

You can install the package via pip:

```bash
pip install sparqlsmith
```

## Quick Start

Here's a simple example of how to use SPARQLsmith:

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

## Features

- Craft SPARQL queries with precision and elegance
- Comprehensive support for:
  - Basic Graph Patterns (BGP)
  - UNION operations
  - OPTIONAL patterns
  - Filters
  - Subqueries
  - ORDER BY clauses
- Intelligent query isomorphism checking
- Sophisticated triple pattern extraction
- Clean query string generation
- Built-in query validation and optimization

## Documentation

For full documentation, visit [docs/](docs/).

## Development

To set up the development environment:

```bash
# Clone the repository
git clone https://github.com/yourusername/sparqlsmith.git
cd sparqlsmith

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

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