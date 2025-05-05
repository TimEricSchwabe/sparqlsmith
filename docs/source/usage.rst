Usage
=====


This guide walks through the main capabilities of sparqlsmith, showing how to create, manipulate, analyze, and execute SPARQL queries programmatically.

Creating SPARQL Queries
-----------------------

Let's start by creating a simple SPARQL query:

.. code-block:: python

    from sparqlsmith.query import SPARQLQuery, BGP, TriplePattern

    # Create a basic graph pattern
    bgp = BGP([
        TriplePattern('?s', '?p', '?o')
    ])

    # Create a query with the BGP as the WHERE clause
    query = SPARQLQuery(
        projection_variables=['?s', '?p', '?o'],
        where_clause=bgp
    )

    # Print the query as a SPARQL string
    print('Sparql String:')
    print(query.to_query_string())

    print('-'*50)
    print('Query Object:')
    print(query)

This will generate a SPARQL query string and print the structure of the query:

.. code-block:: shell

    Sparql String:
    SELECT ?s ?p ?o
    WHERE {
    ?s ?p ?o .
    }
    --------------------------------------------------
    Query Object:
    SPARQLQuery:
    Projection: ?s ?p ?o
    Where Clause:
        BGP:
        Triple: ?s ?p ?o


UNION and OPTIONAL Operators
----------------------------

You can add UNION and OPTIONAL operators to your queries:

.. code-block:: python

    from sparqlsmith.query import SPARQLQuery, BGP, TriplePattern, UnionOperator, OptionalOperator

    # Example 1: Query with OPTIONAL operator
    # Create a basic graph pattern
    main_bgp = BGP([
        TriplePattern('?person', '<http://example.org/name>', '?name')
    ])

    # Create an optional pattern
    optional_bgp = BGP([
        TriplePattern('?person', '<http://example.org/email>', '?email')
    ])

    # Create a query with the main BGP and optional pattern
    query_with_optional = SPARQLQuery(
        projection_variables=['?person', '?name', '?email'],
        where_clause=[main_bgp, OptionalOperator(bgp=optional_bgp)]
    )

    print(query_with_optional.to_query_string())

    # Example 2: Query with UNION operator
    # Create two BGPs for the union
    left_bgp = BGP([
        TriplePattern('?person', '<http://example.org/worksAt>', '?company')
    ])

    right_bgp = BGP([
        TriplePattern('?person', '<http://example.org/contractsWith>', '?company')
    ])

    # Create a query with a UNION operator
    query_with_union = SPARQLQuery(
        projection_variables=['?person', '?company'],
        where_clause=UnionOperator(
            left=left_bgp,
            right=right_bgp
        )
    )
    
    print(query_with_union.to_query_string())
    

Adding Elements to Queries
-------------------------

You can incrementally build more complex queries by adding different components using the ``add()`` method:

.. code-block:: python

    from sparqlsmith.query import (
        SPARQLQuery, BGP, TriplePattern, UnionOperator, 
        OptionalOperator, Filter
    )
    
    # Start with an empty query
    query = SPARQLQuery()
    
    # Add projection variables
    query.projection_variables = ['?person', '?name', '?email']
    
    # Create a BGP for the main pattern
    person_bgp = BGP()
    person_bgp.add(("?person", "<http://example.org/type>", "<http://example.org/Person>"))
    person_bgp.add(("?person", "<http://example.org/name>", "?name"))
    
    # Add a filter to the BGP
    person_bgp.add(Filter("REGEX(?name, '^A', 'i')"))
    
    # Add the BGP to the query
    query.add(person_bgp)
    
    # Create an optional pattern for email
    email_bgp = BGP()
    email_bgp.add(("?person", "<http://example.org/email>", "?email"))
    optional_op = OptionalOperator(bgp=email_bgp)
    
    # Add the optional pattern to the query
    query.add(optional_op)
    
    # Add a top-level filter to the query
    query.add(Filter("?person != <http://example.org/excluded>"))
    
    # Set the query to return DISTINCT results
    query.set_distinct(True)
    
    # Print the query
    print(query.to_query_string())

This generates the following SPARQL query:

.. code-block:: sparql

    SELECT DISTINCT ?person ?name ?email
    WHERE {
      ?person <http://example.org/type> <http://example.org/Person> .
      ?person <http://example.org/name> ?name .
      FILTER(REGEX(?name, '^A', 'i'))
      OPTIONAL {
        ?person <http://example.org/email> ?email .
      }
      FILTER(?person != <http://example.org/excluded>)
    }

Removing Elements from Queries
------------------------------

Similar, you can remove elements from a query using the ``remove()`` method:

.. code-block:: python

    # Remove a triple pattern
    triple_to_remove = person_bgp.triples[1]
    triple_to_remove.remove()

    # Remove a filter
    filter_to_remove = person_bgp.filters[0]  # The REGEX filter
    filter_to_remove.remove()

    # Remove an optional pattern
    optional_op.remove()

Instantiation
-------------

You can instantiate variables in the query using the ``instantiate()`` method:

.. code-block:: python

    from sparqlsmith.query import SPARQLQuery, BGP, TriplePattern

    # Create a query with variables
    bgp = BGP([
        TriplePattern('?person', '<http://example.org/name>', '?name'),
        TriplePattern('?person', '<http://example.org/age>', '?age')
    ])
    
    query = SPARQLQuery(
        projection_variables=['?person', '?name', '?age'],
        where_clause=bgp
    )
    
    # Instantiate variables with concrete values
    instantiated_query = query.instantiate({
        '?name': '"John Doe"',
        '?age': '42'
    })
    
    # Print the instantiated query
    print(instantiated_query.to_query_string())

    


Aggregations and Grouping
-------------------------------

You can add GROUP BY and HAVING clauses:

.. code-block:: python

    from sparqlsmith.query import AggregationExpression, BGP, TriplePattern, SPARQLQuery

    query = SPARQLQuery()
    bgp = BGP([
        TriplePattern('?person', ':name', '?name'),
        TriplePattern('?person', ':age', '?age')
    ])
    query.add(bgp)

    # Create an aggregation
    agg = AggregationExpression(
        function="COUNT",
        variable="?person",
        alias="?count",
        distinct=False
    )

    # Add GROUP BY and aggregation together
    query.add_group_by('?age', aggregations=agg)
    query.projection_variables = ['?age', '?count']



Parsing SPARQL Query Strings
---------------------------

You can parse SPARQL query strings into query objects:

.. code-block:: python

    from sparqlsmith.parser import SPARQLParser
    
    # Parse a SPARQL query string
    parser = SPARQLParser()
    query_string = """
    SELECT DISTINCT ?person ?name 
    WHERE { 
        ?person <http://example.org/name> ?name .
        ?person <http://example.org/age> ?age .
        FILTER(?age > 25)
        OPTIONAL { ?person <http://example.org/email> ?email . }
    }
    """
    
    # Parse the string into a query object
    query_obj = parser.parse_to_query(query_string)
    
    # Print the structure of the parsed query
    print(query_obj)
    
This will generate the following SPARQL object:

.. code-block:: shell

    SPARQLQuery:
    Projection: ?person ?name
    Where Clause:
        GroupGraphPattern:
        BGP:
            Triple: ?person <http://example.org/name> ?name
            Triple: ?person <http://example.org/age> ?age
            Filters:
            ?age > 25
        GroupGraphPattern:
        OPTIONAL:
            BGP:
            Triple: ?person <http://example.org/email> ?email
    

Query Analysis
-------------

You can quickly analyze certain properties of a query:

.. code-block:: python

    # Get analysis information about the query
    print(f"Number of triple patterns: {query_obj.n_triple_patterns}")
    print(f"Number of BGPs: {query_obj.count_bgps()}")
    print(f"All variables: {query_obj.get_all_variables()}")
    print(f"Projection variables: {query_obj.projection_variables}")
    
    # Analyze the shape of the graph defined by a BGP
    bgp = query_obj.where_clause[0] 
    print(f"BGP shape: {bgp.shape()}")


Query Isomorphism
----------------

SPARQLsmith allows you to check if the where clauses of two queries are isomorphic. This extends the isomorphism definition
to include UNION and OPTIONAL operators:

.. code-block:: python

    # Create two queries with different variable names but the same structure
    query1 = SPARQLQuery(
        projection_variables=['?s'],
        prefixes={'ex': '<http://example.com>'},
        where_clause=UnionOperator(
            left=BGP([TriplePattern('?s', 'ex:p', '?o1')]),
            right=BGP([TriplePattern('?s', 'ex:q', '?o2')])
        )
    )
    # Different variable names and BGPs in the UNION operator are switched
    query2 = SPARQLQuery(
        projection_variables=['?subject'],  
        prefixes={'ex': '<http://example.com>'},
        where_clause=UnionOperator(
            left=BGP([TriplePattern('?subject', 'ex:q', '?object2')]),
            right=BGP([TriplePattern('?subject', 'ex:p', '?object1')])
        )
    )

    # Check if the queries are isomorphic
    are_isomorphic = query1.is_isomorphic(query2)
    print(f"Queries are isomorphic: {are_isomorphic}")  # Will print True

    


Running Queries Against SPARQL Endpoints
--------------------------------------

Sparqlsmith can execute queries against SPARQL endpoints:

.. code-block:: python

    # Create a query to get information about Berlin from DBpedia
    query = SPARQLQuery(
        prefixes={"dbo": "http://dbpedia.org/ontology/",
                 "dbr": "http://dbpedia.org/resource/"},
        projection_variables=["?label", "?population"]
    )
    
    # Create a basic graph pattern
    bgp = BGP([
        TriplePattern(
            subject="dbr:Berlin",
            predicate="rdfs:label",
            object="?label"
        ),
        TriplePattern(
            subject="dbr:Berlin",
            predicate="dbo:populationTotal",
            object="?population"
        )
    ])
    
    # Add a filter for English labels
    bgp.add(Filter("LANG(?label) = 'en'"))
    
    # Add the BGP to the query
    query.add(bgp)
    
    # Set a limit
    query.set_limit(5)
    
    # Run the query against DBpedia
    results = query.run("https://dbpedia.org/sparql")
    
    # Process the results
    bindings = results["results"]["bindings"]
    for binding in bindings:
        print(f"Label: {binding['label']['value']}")
        print(f"Population: {binding['population']['value']}")
