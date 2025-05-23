#!/usr/bin/env python3

from sparqlsmith.parser import SPARQLParser
import logging
import pyparsing

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Enable debug
pyparsing.enable_all_warnings()

def test_query(query_str, preserve_nesting=False):

    print("--------------------------------")
    print("--------------------------------")

    print(f"Testing Query: {query_str}")
    print(f"Preserve Nesting: {preserve_nesting}")

    print("--------------------------------")


    """Test parsing of a basic SPARQL query."""
    parser = SPARQLParser(preserve_nesting=preserve_nesting)
    
    # Parse to structured dict
    result = parser.parse(query_str)
    print(f"Structured dict: {result}")
    print("--------------------------------")
    
    # Convert to SPARQLQuery object
    query_obj = parser.structured_dict_to_query(result)

    # print the query object
    query_obj.print_structure()

    print("--------------------------------")
    

    print(f"Query string: {query_obj.to_query_string()}")
    


if __name__ == "__main__":

    # Test with nested braces - comparing flattened vs preserved nesting
    print("\n===== Testing with flattened nesting (default) =====")
    test_query("SELECT ?s ?p ?o WHERE { { { ?s ?p ?o . } } }", preserve_nesting=False)
    
    print("\n===== Testing with preserved nesting =====")
    test_query("SELECT ?s ?p ?o WHERE { { { ?s ?p ?o . } } }", preserve_nesting=True)
    
    # Complex query with nesting and other SPARQL features
    print("\n===== Complex nested query with preserved nesting =====")
    test_query("""
        SELECT ?s ?p ?o
        WHERE { 
            { 
                ?s ?p ?o . 
                OPTIONAL { ?o ?p2 ?x . } 
            }
            UNION
            { 
                { ?o ?p ?s . } 
                FILTER(?s != ?o)
            }
        }
    """, preserve_nesting=True)

    exit()


    test_query("""
            SELECT DISTINCT ?age (COUNT(?person) AS ?count)
            WHERE { 
                ?person :name ?name .
                ?person :age ?age .
                ?person :salary ?salary .
            }
            GROUP BY ?age
            HAVING((COUNT(?person) > 10) &&  (AVG(?salary) > 10000))
        """
    )

    exit()

    test_query("""
        SELECT * 
        WHERE { 
            ?person :name ?name .
            ?person :age ?age .
        }
        ORDER BY DESC(?age)
    """)
    
    test_query("""
        SELECT * 
        WHERE { 
            ?person :name ?name .
            ?person :age ?age .
            ?person :email ?email .
        }
        ORDER BY DESC(?age) ASC(?email) DESC(?name)
    """)

    exit()

    
    test_query("SELECT ?s ?p ?o WHERE { { ?s ?p ?o . } UNION { ?o ?p ?s . } }")


    test_query("SELECT ?s ?p ?o WHERE { ?s ?p ?o . OPTIONAL { ?o ?p ?x . } }")

    # test with filter
    test_query("SELECT ?s ?p ?o WHERE { ?s ?p ?o . FILTER(?o > 5) }")

    # nested query
    test_query("SELECT ?s ?p ?o WHERE { { { ?s ?p ?o . } } }")

    # complex query
    test_query("""
        SELECT DISTINCT ?person ?name 
        WHERE { 
            ?person :name ?name .
            ?person :age ?age .
            FILTER(?age > 25)
            OPTIONAL { ?person :email ?email . }
            { ?person :likes ?hobby . } UNION { ?hobby :likedBy ?person . }
        }
    """)

    test_query("""SELECT ?s ?p ?o
WHERE { ?x ?p ?o.
    { ?s ?p ?o . } UNION { ?o ?p ?s . }
}""")