import unittest
from sparqlsmith import (
    SPARQLQuery,
    BGP,
    TriplePattern,
    UnionOperator,
    OptionalOperator,
    extract_triple_patterns
)
from sparqlsmith.parser import SPARQLParser
from sparqlsmith.errors import OrderByValidationError
from sparqlsmith.query import AggregationExpression

class TestSPARQLQuery(unittest.TestCase):
    def test_query_isomorphism_simple_bgp(self):
        # Test for simple BGP - positive case
        bgp = BGP([
            TriplePattern('?s', ':p', '?o'),
            TriplePattern('?s', '?p2', '?o2')
        ])
        query = SPARQLQuery(
            projection_variables=['?s', '?p', '?o'],
            where_clause=bgp
        )

        bgp2 = BGP([
            TriplePattern('?s1', '?p4', '?o3'),
            TriplePattern('?s1', ':p', '?o5')
        ])
        query2 = SPARQLQuery(
            projection_variables=['?s', '?p', '?o'],
            where_clause=bgp2
        )

        self.assertTrue(query.is_isomorphic(query2))

    def test_query_isomorphism_union(self):
        query = SPARQLQuery(
            projection_variables=['*'],
            where_clause=UnionOperator(
                left=UnionOperator(
                    left=BGP([TriplePattern('?s1', '?p1', '?o1')]),
                    right=BGP([TriplePattern('?o1', '?p2', '?o2')])
                ),
                right=BGP([TriplePattern('?s1', ':p22', '?o23')])
            )
        )
        query2 = SPARQLQuery(
            projection_variables=['*'],
            where_clause=UnionOperator(
                left=BGP([TriplePattern('?s11', ':p22', '?o23')]),
                right=UnionOperator(
                    left=BGP([TriplePattern('?s11', '?p1', '?o1')]),
                    right=BGP([TriplePattern('?o1', '?p2', '?o2')])
                )
            )
        )

        self.assertTrue(query.is_isomorphic(query2))

    def test_query_isomorphism_optional(self):
        # Main BGP
        main_bgp = BGP([
            TriplePattern('?s', '?p', '?o')
        ])
        # First OPTIONAL
        optional1 = OptionalOperator(
            bgp=BGP([
                TriplePattern('?s', ':p1', '?o2')
            ])
        )

        where_clause = [main_bgp, optional1]

        query = SPARQLQuery(
            projection_variables=['?s'],
            where_clause=where_clause
        )

        main_bgp = BGP([
            TriplePattern('?s2', '?p3', '?o1')
        ])
        optional1 = OptionalOperator(
            bgp=BGP([
                TriplePattern('?s2', ':p1', '?o2')
            ])
        )

        where_clause = [main_bgp, optional1]

        query2 = SPARQLQuery(
            projection_variables=['?s'],
            where_clause=where_clause
        )

        self.assertTrue(query.is_isomorphic(query2))

    def test_extract_triple_patterns(self):
        query = SPARQLQuery(
            projection_variables=['*'],
            where_clause=UnionOperator(
                left=UnionOperator(
                    left=BGP([TriplePattern('?s1', '?p1', '?o1')]),
                    right=BGP([TriplePattern('?o1', '?p2', '?o2')])
                ),
                right=BGP([TriplePattern('?s1', '?p22', '?o22')])
            )
        )

        triple_patterns = extract_triple_patterns(query)
        self.assertEqual(len(triple_patterns), 3)
        
        # Verify the extracted patterns
        expected_patterns = [
            TriplePattern('?s1', '?p1', '?o1'),
            TriplePattern('?o1', '?p2', '?o2'),
            TriplePattern('?s1', '?p22', '?o22')
        ]
        
        for tp, expected_tp in zip(triple_patterns, expected_patterns):
            self.assertEqual(tp.subject, expected_tp.subject)
            self.assertEqual(tp.predicate, expected_tp.predicate)
            self.assertEqual(tp.object, expected_tp.object)

    def test_distinct_query_serialization(self):
        """Test that the is_distinct parameter affects the query string output correctly"""
        # Create a query with is_distinct=True
        bgp = BGP([TriplePattern('?s', '?p', '?o')])
        query = SPARQLQuery(
            projection_variables=['?s', '?p', '?o'],
            where_clause=bgp,
            is_distinct=True
        )
        
        # Check query string contains DISTINCT
        query_str = query.to_query_string()
        self.assertIn("SELECT DISTINCT", query_str)
        
        # Create a query with is_distinct=False
        query = SPARQLQuery(
            projection_variables=['?s', '?p', '?o'],
            where_clause=bgp,
            is_distinct=False
        )
        
        # Check query string does not contain DISTINCT
        query_str = query.to_query_string()
        self.assertNotIn("DISTINCT", query_str)
        
        # Check that distinct flag is preserved when creating copy
        query = SPARQLQuery(
            projection_variables=['?s', '?p', '?o'],
            where_clause=bgp,
            is_distinct=True
        )
        query_copy = query.copy()
        self.assertTrue(query_copy.is_distinct)
        
        # Test with copy while overriding the is_distinct parameter
        query_copy = query.copy(is_distinct=False)
        self.assertFalse(query_copy.is_distinct)

class TestSPARQLParser(unittest.TestCase):
    def setUp(self):
        self.parser = SPARQLParser()
        
    def _parse_and_verify(self, query_str):
        """Helper method to parse a query and do basic verification"""
        result = self.parser.parse(query_str)
        query_obj = self.parser.structured_dict_to_query(result)
        
        # Verify that the query can be converted back to a string
        query_str_result = query_obj.to_query_string()
        self.assertIsInstance(query_str_result, str)
        
            
        return query_obj
        
    def test_simple_select_query(self):
        """Test parsing of a simple SELECT query with two triple patterns"""
        query_str = """
            SELECT * 
            WHERE { 
                ?person :name ?name .
                ?person :age ?age .
            }
        """
        query_obj = self._parse_and_verify(query_str)
        
        # Check basic properties
        self.assertEqual(query_obj.projection_variables, ['*'])
        
        # Verify the where clause contains 2 triple patterns
        self.assertIsInstance(query_obj.where_clause, BGP)
        self.assertEqual(len(query_obj.where_clause.triples), 2)
        
    def test_union_query(self):
        """Test parsing of a UNION query"""
        query_str = "SELECT ?s ?p ?o WHERE { { ?s ?p ?o . } UNION { ?o ?p ?s . } }"
        query_obj = self._parse_and_verify(query_str)
        
        # Check that the where clause is a UnionOperator
        self.assertIsInstance(query_obj.where_clause, UnionOperator)
        
        # Verify both sides of the UNION
        self.assertIsInstance(query_obj.where_clause.left, BGP)
        self.assertIsInstance(query_obj.where_clause.right, BGP)
        
        self.assertEqual(len(query_obj.where_clause.left.triples), 1)
        self.assertEqual(len(query_obj.where_clause.right.triples), 1)
        
    def test_optional_query(self):
        """Test parsing of a query with OPTIONAL pattern"""
        query_str = "SELECT ?s ?p ?o WHERE { ?s ?p ?o . OPTIONAL { ?o ?p ?x . } }"
        query_obj = self._parse_and_verify(query_str)
        
        # For queries with multiple patterns, we expect a list in where_clause
        self.assertIsInstance(query_obj.where_clause, list)
        self.assertEqual(len(query_obj.where_clause), 2)
        
        # First element should be a BGP
        self.assertIsInstance(query_obj.where_clause[0], BGP)
        
        # Second element should be an OptionalOperator
        self.assertIsInstance(query_obj.where_clause[1], OptionalOperator)
        
    def test_filter_query(self):
        """Test parsing of a query with FILTER"""
        query_str = "SELECT ?s ?p ?o WHERE { ?s ?p ?o . FILTER(?o > 5) }"
        query_obj = self._parse_and_verify(query_str)
        
        # Verify the filter exists
        self.assertIsNotNone(query_obj.filters)
        self.assertEqual(len(query_obj.filters), 1)
        self.assertEqual(query_obj.filters[0].expression, "?o > 5")
        
    def test_nested_query(self):
        """Test parsing of a nested query with braces"""
        query_str = "SELECT ?s ?p ?o WHERE { { { ?s ?p ?o . } } }"
        query_obj = self._parse_and_verify(query_str)
        
        # The nested structure should be flattened to a simple BGP
        self.assertIsInstance(query_obj.where_clause, BGP)
        self.assertEqual(len(query_obj.where_clause.triples), 1)
        
    def test_complex_query(self):
        """Test parsing of a complex query with DISTINCT, FILTER, OPTIONAL, and UNION"""
        query_str = """
            SELECT DISTINCT ?person ?name 
            WHERE { 
                ?person :name ?name .
                ?person :age ?age .
                FILTER(?age > 25)
                OPTIONAL { ?person :email ?email . }
                { ?person :likes ?hobby . } UNION { ?hobby :likedBy ?person . }
            }
        """
        query_obj = self._parse_and_verify(query_str)
        
        # Check projection variables
        self.assertEqual(query_obj.projection_variables, ['?person', '?name'])
        
        # Verify DISTINCT flag
        self.assertTrue(query_obj.is_distinct)
        
        # Check filter
        self.assertIsNotNone(query_obj.filters)
        self.assertEqual(len(query_obj.filters), 1)
        self.assertEqual(query_obj.filters[0].expression, "?age > 25")
        
        # The where clause should be a list of patterns
        self.assertIsInstance(query_obj.where_clause, list)
        
        # Find and verify the UNION structure
        union_element = None
        for element in query_obj.where_clause:
            if isinstance(element, UnionOperator):
                union_element = element
                break
                
        self.assertIsNotNone(union_element)
        self.assertIsInstance(union_element.left, BGP)
        self.assertIsInstance(union_element.right, BGP)
        
    def test_nested_union_query(self):
        """Test parsing of a query with nested UNION patterns"""
        query_str = """SELECT ?s ?p ?o
        WHERE { ?x ?p ?o.
            { ?s ?p ?o . } UNION { ?o ?p ?s . }
        }"""
        query_obj = self._parse_and_verify(query_str)
        
        # For queries with multiple patterns, we expect a list in where_clause
        self.assertIsInstance(query_obj.where_clause, list)
        
        # Find and verify the BGP and UNION
        has_bgp = False
        has_union = False
        
        for element in query_obj.where_clause:
            if isinstance(element, BGP):
                has_bgp = True
            elif isinstance(element, UnionOperator):
                has_union = True
                
        self.assertTrue(has_bgp)
        self.assertTrue(has_union)

    def test_distinct_query_parsing(self):
        """Test parsing of DISTINCT queries"""
        # Query with DISTINCT
        query_str = "SELECT DISTINCT ?s ?p ?o WHERE { ?s ?p ?o . }"
        query_obj = self._parse_and_verify(query_str)
        
        # Confirm projection variables
        self.assertEqual(query_obj.projection_variables, ['?s', '?p', '?o'])
        
        # Check serialization
        query_str_result = query_obj.to_query_string()
        self.assertIn("SELECT DISTINCT", query_str_result)
        
        # Query without DISTINCT
        query_str = "SELECT ?s ?p ?o WHERE { ?s ?p ?o . }"
        query_obj = self._parse_and_verify(query_str)
        
        # Confirm distinct flag is not set
        self.assertFalse(query_obj.is_distinct)
        
        # Check serialization doesn't have DISTINCT
        query_str_result = query_obj.to_query_string()
        self.assertNotIn("DISTINCT", query_str_result)

    def test_simple_order_by(self):
        """Test parsing of a query with simple ORDER BY clause"""
        query_str = """
            SELECT ?person ?name ?age 
            WHERE { 
                ?person :name ?name .
                ?person :age ?age .
            }
            ORDER BY ?age
        """
        query_obj = self._parse_and_verify(query_str)
        
        # Verify the order_by attribute exists
        self.assertIsNotNone(query_obj.order_by)
        
        # Check the variables and direction
        self.assertEqual(query_obj.order_by.variables, ['?age'])
        
        # Check the direction is ascending (default)
        if isinstance(query_obj.order_by.ascending, bool):
            self.assertTrue(query_obj.order_by.ascending)
        else:
            self.assertEqual(query_obj.order_by.ascending, [True])
        
        # Check the serialized query contains the ORDER BY
        query_str_result = query_obj.to_query_string()
        self.assertIn("ORDER BY ASC(?age)", query_str_result)

    def test_complex_order_by_with_directions(self):
        """Test parsing of a query with complex ORDER BY clause with mixed directions"""
        query_str = """
            SELECT ?person ?name ?age ?email
            WHERE { 
                ?person :name ?name .
                ?person :age ?age .
                ?person :email ?email .
            }
            ORDER BY ?name DESC(?age) ASC(?email)
        """
        query_obj = self._parse_and_verify(query_str)
        
        # Verify the order_by attribute exists
        self.assertIsNotNone(query_obj.order_by)
        
        # Check the variables are in the correct order
        self.assertEqual(query_obj.order_by.variables, ['?name', '?age', '?email'])
        
        # Check the directions are correct (True for ASC, False for DESC)
        self.assertEqual(query_obj.order_by.ascending, [True, False, True])
        
        # Check the serialized query contains the ORDER BY with correct directions
        query_str_result = query_obj.to_query_string()
        self.assertIn("ORDER BY", query_str_result)
        self.assertIn("ASC(?name)", query_str_result)
        self.assertIn("DESC(?age)", query_str_result)
        self.assertIn("ASC(?email)", query_str_result)


    def test_group_by_parsing(self):
        """Test parsing of a query with GROUP BY clause"""
        query_str = """
            SELECT ?age
            WHERE { 
                ?person :name ?name .
                ?person :age ?age .
            }
            GROUP BY ?age
        """
        query_obj = self._parse_and_verify(query_str)
        
        # Verify the group_by attribute exists
        self.assertIsNotNone(query_obj.group_by)
        
        # Check the group by variables
        self.assertEqual(query_obj.group_by.variables, ['?age'])
        
        # Check the serialized query contains the GROUP BY
        query_str_result = query_obj.to_query_string()
        self.assertIn("GROUP BY ?age", query_str_result)

    def test_aggregate_functions(self):
        """Test parsing of a query with aggregation functions in SELECT"""
        query_str = """
            SELECT ?age (COUNT(?person) AS ?count) (SUM(?salary) AS ?totalSalary)
            WHERE { 
                ?person :name ?name .
                ?person :age ?age .
                ?person :salary ?salary .
            }
            GROUP BY ?age
        """
        query_obj = self._parse_and_verify(query_str)
        
        # Verify regular projection variables
        self.assertIn("?age", query_obj.projection_variables)
        
        # Verify aggregations exist
        self.assertIsNotNone(query_obj.aggregations)
        self.assertEqual(len(query_obj.aggregations), 2)
        
        # Check COUNT aggregation
        count_agg = next((agg for agg in query_obj.aggregations if agg.function == "COUNT"), None)
        self.assertIsNotNone(count_agg)
        self.assertEqual(count_agg.variable, "?person")
        self.assertEqual(count_agg.alias, "?count")
        
        # Check SUM aggregation
        sum_agg = next((agg for agg in query_obj.aggregations if agg.function == "SUM"), None)
        self.assertIsNotNone(sum_agg)
        self.assertEqual(sum_agg.variable, "?salary")
        self.assertEqual(sum_agg.alias, "?totalSalary")
        
        # Check serialization
        query_str_result = query_obj.to_query_string()
        self.assertIn("(COUNT(?person) AS ?count)", query_str_result)
        self.assertIn("(SUM(?salary) AS ?totalSalary)", query_str_result)
        self.assertIn("GROUP BY ?age", query_str_result)

        
    def test_aggregate_with_distinct(self):
        """Test parsing of aggregate function with DISTINCT"""
        query_str = """
            SELECT (COUNT(DISTINCT ?person) AS ?uniqueCount)
            WHERE { 
                ?person :name ?name .
            }
        """
        query_obj = self._parse_and_verify(query_str)
        
        # Verify aggregation exists and has DISTINCT flag
        self.assertEqual(len(query_obj.aggregations), 1)
        agg = query_obj.aggregations[0]
        self.assertEqual(agg.function, "COUNT")
        self.assertEqual(agg.variable, "?person")
        self.assertEqual(agg.alias, "?uniqueCount")
        self.assertTrue(agg.distinct)
        
        # Check serialization
        query_str_result = query_obj.to_query_string()
        self.assertIn("(COUNT(DISTINCT ?person) AS ?uniqueCount)", query_str_result)
        
    def test_count_star_aggregation(self):
        """Test parsing of COUNT(*) aggregation"""
        query_str = """
            SELECT (COUNT(*) AS ?total)
            WHERE { 
                ?person :name ?name .
            }
        """
        query_obj = self._parse_and_verify(query_str)
        
        # Verify COUNT(*) aggregation
        self.assertEqual(len(query_obj.aggregations), 1)
        agg = query_obj.aggregations[0]
        self.assertEqual(agg.function, "COUNT")
        self.assertEqual(agg.variable, "*")
        self.assertEqual(agg.alias, "?total")
        
        # Check serialization
        query_str_result = query_obj.to_query_string()
        self.assertIn("(COUNT(*) AS ?total)", query_str_result)

    def test_having_clause(self):
        """Test parsing of a query with HAVING clause"""
        query_str = """
            SELECT DISTINCT ?age (COUNT(?person) AS ?count)
            WHERE { 
                ?person :name ?name .
                ?person :age ?age .
                ?person :salary ?salary .
            }
            GROUP BY ?age
            HAVING(COUNT(?person) > 10)
        """
        query_obj = self._parse_and_verify(query_str)
        
        # Verify the having attribute exists
        self.assertIsNotNone(query_obj.having)
        self.assertEqual(len(query_obj.having), 1)
        
        # Check the having expression is correctly parsed
        self.assertEqual(query_obj.having[0].expression, "COUNT(?person) > 10")
        
        # Check the serialized query contains the HAVING clause
        query_str_result = query_obj.to_query_string()
        self.assertIn("HAVING(COUNT(?person) > 10)", query_str_result)
        
        # Also verify that the other parts of the query are correct
        self.assertTrue(query_obj.is_distinct)
        self.assertIsNotNone(query_obj.group_by)
        self.assertEqual(query_obj.group_by.variables, ['?age'])
        self.assertEqual(len(query_obj.aggregations), 1)
        self.assertEqual(query_obj.aggregations[0].function, "COUNT")
        self.assertEqual(query_obj.aggregations[0].variable, "?person")
        self.assertEqual(query_obj.aggregations[0].alias, "?count")

    def test_complex_having_clause(self):
        """Test parsing of a query with complex HAVING clause using logical operators"""
        query_str = """
            SELECT DISTINCT ?age (COUNT(?person) AS ?count)
            WHERE { 
                ?person :name ?name .
                ?person :age ?age .
                ?person :salary ?salary .
            }
            GROUP BY ?age
            HAVING((COUNT(?person) > 10) AND (AVG(?salary) > 10000))
        """
        query_obj = self._parse_and_verify(query_str)
        
        # Verify the having attribute exists
        self.assertIsNotNone(query_obj.having)
        self.assertEqual(len(query_obj.having), 1)
        
        # Check the having expression is correctly parsed and includes the AND operator
        having_expr = query_obj.having[0].expression
        self.assertIn("COUNT(?person) > 10", having_expr)
        self.assertIn("AND", having_expr)
        self.assertIn("AVG(?salary) > 10000", having_expr)
        
        # Check the serialized query contains the complete HAVING clause
        query_str_result = query_obj.to_query_string()
        self.assertIn("HAVING", query_str_result)
        self.assertIn("COUNT(?person) > 10", query_str_result)
        self.assertIn("AND", query_str_result)
        self.assertIn("AVG(?salary) > 10000", query_str_result)

if __name__ == '__main__':
    unittest.main() 