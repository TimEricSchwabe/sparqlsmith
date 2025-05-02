#!/usr/bin/env python3
import json
from sparqlsmith.query import SPARQLQuery, BGP, Filter, OptionalOperator, TriplePattern

def print_results(results, limit=5):
    """Pretty print the results of a SPARQL query"""
    if "error" in results:
        print(f"Error: {results['message']}")
        print(f"Query: {results['query']}")
        return

    if "results" not in results:
        print("No results structure found in response")
        print(json.dumps(results, indent=2))
        return

    bindings = results["results"]["bindings"]
    count = len(bindings)
    
    print(f"Found {count} results")
    
    if count == 0:
        return
        
    # Get the variable names from the first result
    variables = results["head"]["vars"]
    
    # Print header
    header = " | ".join(variables)
    print("-" * len(header))
    print(header)
    print("-" * len(header))
    
    # Print results (limited to first few)
    for binding in bindings[:limit]:
        row = []
        for var in variables:
            if var in binding:
                value = binding[var]["value"]
                # Truncate long values
                if len(value) > 50:
                    value = value[:47] + "..."
                row.append(value)
            else:
                row.append("")
        print(" | ".join(row))
    
    if count > limit:
        print(f"... and {count - limit} more results")
    print("-" * len(header))


def example_1_basic_query():
    """Simple query to get information about Berlin"""
    print("\n=== Example 1: Basic Query ===")
    
    # Create a query to get information about Berlin
    query = SPARQLQuery(
        prefixes={"dbo": "http://dbpedia.org/ontology/",
                 "dbr": "http://dbpedia.org/resource/"},
        projection_variables=["?label", "?population", "?abstract"]
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
        ),
        TriplePattern(
            subject="dbr:Berlin",
            predicate="dbo:abstract",
            object="?abstract"
        )
    ])
    
    # Add a filter for English labels
    bgp.add(Filter("LANG(?label) = 'en'"))
    
    # Add the BGP to the query
    query.add(bgp)
    
    # Add a filter for English abstracts
    query.add(Filter("LANG(?abstract) = 'en'"))
    
    # Set a limit to avoid too many results
    query.set_limit(10)
    
    # Print the generated query
    print("Generated SPARQL Query:")
    print(query.to_query_string())
    
    # Run the query against DBpedia
    print("\nExecuting query against DBpedia...")
    results = query.run("https://dbpedia.org/sparql")
    
    # Print the results
    print_results(results)


def example_2_optional_query():
    """Query with OPTIONAL patterns"""
    print("\n=== Example 2: Query with OPTIONAL pattern ===")
    
    # Create a query to find information about German cities
    query = SPARQLQuery(
        prefixes={
            "dbo": "http://dbpedia.org/ontology/",
            "dbr": "http://dbpedia.org/resource/",
            "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
            "rdfs": "http://www.w3.org/2000/01/rdf-schema#"
        },
        projection_variables=["?city", "?name", "?population", "?area"]
    )
    
    # Main BGP for cities in Germany
    main_bgp = BGP([
        TriplePattern(
            subject="?city",
            predicate="rdf:type",
            object="dbo:City"
        ),
        TriplePattern(
            subject="?city",
            predicate="dbo:country",
            object="dbr:Germany"
        ),
        TriplePattern(
            subject="?city",
            predicate="rdfs:label",
            object="?name"
        )
    ])
    
    # Add a filter for English names
    main_bgp.add(Filter("LANG(?name) = 'en'"))
    
    # Optional pattern for population
    population_bgp = BGP([
        TriplePattern(
            subject="?city",
            predicate="dbo:populationTotal",
            object="?population"
        )
    ])
    
    # Optional pattern for area
    area_bgp = BGP([
        TriplePattern(
            subject="?city",
            predicate="dbo:areaTotal",
            object="?area"
        )
    ])
    
    # Add the main BGP to the query
    query.add(main_bgp)
    
    # Add optional patterns
    query.add(OptionalOperator(population_bgp))
    query.add(OptionalOperator(area_bgp))
    
    # Set a limit to avoid too many results
    query.set_limit(5)
    
    # Print the generated query
    print("Generated SPARQL Query:")
    print(query.to_query_string())
    
    # Run the query against DBpedia
    print("\nExecuting query against DBpedia...")
    results = query.run("https://dbpedia.org/sparql")
    
    # Print the results
    print_results(results)


def example_3_aggregation_query():
    """Query with aggregation and GROUP BY"""
    print("\n=== Example 3: Query with aggregation and GROUP BY ===")
    
    from sparqlsmith.query import AggregationExpression, GroupBy
    
    # Create a query to count cities by country
    query = SPARQLQuery(
        prefixes={
            "dbo": "http://dbpedia.org/ontology/",
            "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
        },
        projection_variables=["?country"],
        is_distinct=True
    )
    
    # Add aggregation expression
    query.add_aggregation(
        AggregationExpression(
            function="COUNT",
            variable="?city",
            alias="?cityCount",
            distinct=True
        )
    )
    
    # Create BGP for cities and their countries
    bgp = BGP([
        TriplePattern(
            subject="?city",
            predicate="rdf:type",
            object="dbo:City"
        ),
        TriplePattern(
            subject="?city",
            predicate="dbo:country",
            object="?country"
        )
    ])
    
    # Add the BGP to the query
    query.add(bgp)
    
    # Add GROUP BY
    query.add_group_by("?country")
    
    # Add ORDER BY to sort by city count in descending order
    query.add_order_by("?cityCount", ascending=False)
    
    # Set a limit
    query.set_limit(10)
    
    # Print the generated query
    print("Generated SPARQL Query:")
    print(query.to_query_string())
    
    # Run the query against DBpedia
    print("\nExecuting query against DBpedia...")
    results = query.run("https://dbpedia.org/sparql")
    
    # Print the results
    print_results(results)


def main():
    """Run all examples"""
    print("SPARQLsmith Query Execution Examples")
    print("===================================")
    
    try:
        example_1_basic_query()
        example_2_optional_query()
        example_3_aggregation_query()
    except Exception as e:
        print(f"Error running examples: {str(e)}")


if __name__ == "__main__":
    main() 