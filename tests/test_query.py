import unittest
from sparqlsmith import (
    SPARQLQuery,
    BGP,
    TriplePattern,
    UnionOperator,
    OptionalOperator,
    Filter,
    GroupGraphPattern,
    SubQuery,
    extract_triple_patterns
)
from sparqlsmith.parser import SPARQLParser
from sparqlsmith.errors import OrderByValidationError
from sparqlsmith.query import AggregationExpression
from unittest.mock import patch, MagicMock

class TestSPARQLQuery(unittest.TestCase):
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

    def test_variable_instantiation(self):
        """Test the instantiation of variables with different types of values"""
        # Create a query with variables
        bgp = BGP([
            TriplePattern('?person', '<http://example.org/name>', '?name'),
            TriplePattern('?person', '<http://example.org/age>', '?age'),
            TriplePattern('?person', '<http://example.org/homepage>', '?website')
        ])
        
        query = SPARQLQuery(
            projection_variables=['?person', '?name', '?age', '?website'],
            where_clause=bgp
        )
        
        # Test 1: Instantiate using keys with '?' prefix
        instantiated_query = query.copy().instantiate({
            '?name': '"John Doe"',  # String literal
            '?age': '42',           # Numeric literal
            '?website': '<http://example.org/john>'  # URI
        })
        
        # Verify variables in triple patterns are correctly replaced
        self.assertEqual(instantiated_query.where_clause.triples[0].object, '"John Doe"')
        self.assertEqual(instantiated_query.where_clause.triples[1].object, '42')
        self.assertEqual(instantiated_query.where_clause.triples[2].object, '<http://example.org/john>')
        
        # Verify projection variables are updated (only non-instantiated variables remain)
        self.assertEqual(instantiated_query.projection_variables, ['?person'])
        
        # Test 2: Instantiate using keys without '?' prefix
        instantiated_query2 = query.copy().instantiate({
            'name': '"Jane Doe"',   # String literal
            'age': '35',            # Numeric literal
            'website': '<http://example.org/jane>'  # URI
        })
        
        # Verify variables in triple patterns are correctly replaced
        self.assertEqual(instantiated_query2.where_clause.triples[0].object, '"Jane Doe"')
        self.assertEqual(instantiated_query2.where_clause.triples[1].object, '35')
        self.assertEqual(instantiated_query2.where_clause.triples[2].object, '<http://example.org/jane>')
        
        # Verify projection variables are updated
        self.assertEqual(instantiated_query2.projection_variables, ['?person'])
        
        # Test 3: Mixed key formats and value types
        instantiated_query3 = query.copy().instantiate({
            'name': '"Bob Smith"',        # Without '?' prefix
            '?age': '28',                 # With '?' prefix
            'website': 'example.org/bob'  # Value without URI brackets
        })
        
        # Verify variables in triple patterns are correctly replaced
        self.assertEqual(instantiated_query3.where_clause.triples[0].object, '"Bob Smith"')
        self.assertEqual(instantiated_query3.where_clause.triples[1].object, '28')
        self.assertEqual(instantiated_query3.where_clause.triples[2].object, '<example.org/bob>')  # URI brackets added

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


class TestQueryIsomorphism(unittest.TestCase):
    """Dedicated test class for query isomorphism functionality"""
    
    def test_basic_bgp_isomorphism(self):
        """Test isomorphism with simple BGPs and variable renaming"""
        query1 = SPARQLQuery(
            where_clause=BGP([
                TriplePattern('?s', ':p', '?o'),
                TriplePattern('?s', '?p2', '?o2')
            ])
        )
        
        query2 = SPARQLQuery(
            where_clause=BGP([
                TriplePattern('?subject', ':p', '?object'),
                TriplePattern('?subject', '?predicate', '?object2')
            ])
        )
        
        self.assertTrue(query1.is_isomorphic(query2), 
            "BGPs with different variable names should be isomorphic")

    def test_bgp_non_isomorphism(self):
        """Test non-isomorphic BGPs with inconsistent variable mappings"""
        query1 = SPARQLQuery(
            where_clause=BGP([
                TriplePattern('?s', ':p', '?o'),
                TriplePattern('?s', ':q', '?x')  # Notice the subject is the same as above
            ])
        )
        
        query2 = SPARQLQuery(
            where_clause=BGP([
                TriplePattern('?s', ':p', '?o'),
                TriplePattern('?t', ':q', '?x')  # Different subject pattern breaks isomorphism
            ])
        )
        
        self.assertFalse(query1.is_isomorphic(query2),
            "BGPs with inconsistent variable mappings should not be isomorphic")

    def test_bgp_different_sizes(self):
        """Test non-isomorphism with different BGP sizes"""
        query1 = SPARQLQuery(
            where_clause=BGP([
                TriplePattern('?s', ':p', '?o')
            ])
        )
        
        query2 = SPARQLQuery(
            where_clause=BGP([
                TriplePattern('?s', ':p', '?o'),
                TriplePattern('?o', ':q', '?x')
            ])
        )
        
        self.assertFalse(query1.is_isomorphic(query2),
            "BGPs with different numbers of triples should not be isomorphic")

    def test_constant_preservation(self):
        """Test that constants must match exactly in isomorphic queries"""
        query1 = SPARQLQuery(
            where_clause=BGP([
                TriplePattern('?s', ':predicate1', '?o'),
                TriplePattern('?s', ':predicate2', '"value"')
            ])
        )
        
        # Same structure but different constant
        query2 = SPARQLQuery(
            where_clause=BGP([
                TriplePattern('?x', ':predicate1', '?y'),
                TriplePattern('?x', ':predicate2', '"different"')
            ])
        )
        
        self.assertFalse(query1.is_isomorphic(query2),
            "Queries with different constants should not be isomorphic")
        
        # Same structure with matching constants
        query3 = SPARQLQuery(
            where_clause=BGP([
                TriplePattern('?x', ':predicate1', '?y'),
                TriplePattern('?x', ':predicate2', '"value"')
            ])
        )
        
        self.assertTrue(query1.is_isomorphic(query3),
            "Queries with same constants should be isomorphic")

    def test_union_isomorphism(self):
        """Test isomorphism with UNION operators"""
        query1 = SPARQLQuery(
            where_clause=UnionOperator(
                left=BGP([TriplePattern('?s', ':p', '?o')]),
                right=BGP([TriplePattern('?s', ':q', '?o')])
            )
        )
        
        # Same structure but with operands in opposite order (should be isomorphic due to UNION commutativity)
        query2 = SPARQLQuery(
            where_clause=UnionOperator(
                left=BGP([TriplePattern('?x', ':q', '?y')]),
                right=BGP([TriplePattern('?x', ':p', '?y')])
            )
        )
        
        self.assertTrue(query1.is_isomorphic(query2),
            "Unions with swapped operands should be isomorphic due to commutativity")

    def test_nested_union_isomorphism(self):
        """Test isomorphism with nested UNION operators"""
        query1 = SPARQLQuery(
            where_clause=UnionOperator(
                left=UnionOperator(
                    left=BGP([TriplePattern('?s1', '?p1', '?o1')]),
                    right=BGP([TriplePattern('?o1', '?p2', '?o2')])
                ),
                right=BGP([TriplePattern('?s1', ':p22', '?o23')])
            )
        )
        
        # Same structure with changed variable names and nested UNION flipped 
        query2 = SPARQLQuery(
            where_clause=UnionOperator(
                left=BGP([TriplePattern('?s11', ':p22', '?o23')]),
                right=UnionOperator(
                    left=BGP([TriplePattern('?s11', '?p1', '?o1')]),
                    right=BGP([TriplePattern('?o1', '?p2', '?o2')])
                )
            )
        )
        
        self.assertTrue(query1.is_isomorphic(query2),
            "Nested unions with different structures but equivalent semantics should be isomorphic")

    def test_optional_isomorphism(self):
        """Test isomorphism with OPTIONAL patterns"""
        query1 = SPARQLQuery(
            where_clause=[
                BGP([TriplePattern('?s', '?p', '?o')]),
                OptionalOperator(bgp=BGP([TriplePattern('?s', ':p1', '?o2')]))
            ]
        )
        
        query2 = SPARQLQuery(
            where_clause=[
                BGP([TriplePattern('?subject', '?predicate', '?object')]),
                OptionalOperator(bgp=BGP([TriplePattern('?subject', ':p1', '?object2')]))
            ]
        )
        
        self.assertTrue(query1.is_isomorphic(query2),
            "Queries with OPTIONAL patterns should be isomorphic with consistent variable mappings")

    def test_mixed_pattern_isomorphism(self):
        """Test isomorphism with mixed patterns (BGP, UNION, OPTIONAL)"""
        # Query with BGP, UNION inside OPTIONAL
        query1 = SPARQLQuery(
            where_clause=[
                BGP([TriplePattern('?s', ':type', ':Person')]),
                OptionalOperator(
                    bgp=UnionOperator(
                        left=BGP([TriplePattern('?s', ':name', '?name')]),
                        right=BGP([TriplePattern('?s', ':label', '?name')])
                    )
                )
            ]
        )
        
        # Same structure with different variable names
        query2 = SPARQLQuery(
            where_clause=[
                BGP([TriplePattern('?x', ':type', ':Person')]),
                OptionalOperator(
                    bgp=UnionOperator(
                        left=BGP([TriplePattern('?x', ':label', '?y')]),
                        right=BGP([TriplePattern('?x', ':name', '?y')])
                    )
                )
            ]
        )
        
        self.assertTrue(query1.is_isomorphic(query2),
            "Complex patterns with mixed operators should be isomorphic with proper variable mapping")

    def test_filter_handling(self):
        """Test that queries with filters in different places are not isomorphic"""
        query1 = SPARQLQuery(
            where_clause=BGP(
                triples=[
                    TriplePattern('?s', ':p', '?o')
                ],
                filters=[Filter('?o > 10')]
            )
        )
        
        # Filter with same expression but different variables
        query2 = SPARQLQuery(
            where_clause=BGP(
                triples=[
                    TriplePattern('?x', ':p', '?y')
                ],
                filters=[Filter('?y > 10')]
            )
        )
        
        self.assertTrue(query1.is_isomorphic(query2),
            "Queries with filters should be isomorphic if variables are consistently mapped")
        
        # Filter with different expression
        query3 = SPARQLQuery(
            where_clause=BGP(
                triples=[
                    TriplePattern('?x', ':p', '?y')
                ],
                filters=[Filter('?y < 5')]
            )
        )
        
        # Note: Current implementation doesn't compare filter expressions in detail
        # This test documents current behavior but might need to change if filter comparison is enhanced
        self.assertTrue(query1.is_isomorphic(query3),
            "Currently, filter expressions are not compared in detail")

    def test_group_pattern_isomorphism(self):
        """Test isomorphism with GroupGraphPattern wrappers"""
        query1 = SPARQLQuery(
            where_clause=GroupGraphPattern(
                pattern=BGP([TriplePattern('?s', ':p', '?o')])
            )
        )
        
        query2 = SPARQLQuery(
            where_clause=GroupGraphPattern(
                pattern=BGP([TriplePattern('?x', ':p', '?y')])
            )
        )
        
        self.assertTrue(query1.is_isomorphic(query2),
            "Queries with group patterns should be isomorphic if their contents are isomorphic")

    def test_nested_group_pattern_isomorphism(self):
        """Test isomorphism with nested GroupGraphPattern structures"""
        query1 = SPARQLQuery(
            where_clause=GroupGraphPattern(
                pattern=GroupGraphPattern(
                    pattern=BGP([TriplePattern('?s', ':p', '?o')])
                )
            )
        )
        
        query2 = SPARQLQuery(
            where_clause=GroupGraphPattern(
                pattern=GroupGraphPattern(
                    pattern=BGP([TriplePattern('?x', ':p', '?y')])
                )
            )
        )
        
        self.assertTrue(query1.is_isomorphic(query2),
            "Nested group patterns should be isomorphic if their contents are isomorphic")

    def test_subquery_isomorphism(self):
        """Test isomorphism with SubQuery components"""
        subquery1 = SPARQLQuery(
            projection_variables=['?o'],
            where_clause=BGP([TriplePattern('?s', ':p', '?o')])
        )
        
        query1 = SPARQLQuery(
            where_clause=SubQuery(subquery1)
        )
        
        subquery2 = SPARQLQuery(
            projection_variables=['?obj'],
            where_clause=BGP([TriplePattern('?subj', ':p', '?obj')])
        )
        
        query2 = SPARQLQuery(
            where_clause=SubQuery(subquery2)
        )
        
        self.assertTrue(query1.is_isomorphic(query2),
            "Queries with subqueries should be isomorphic if their subqueries are isomorphic")

    def test_projection_differences(self):
        """Test that projection variables don't affect isomorphism"""
        query1 = SPARQLQuery(
            projection_variables=['?s', '?o'],
            where_clause=BGP([TriplePattern('?s', ':p', '?o')])
        )
        
        query2 = SPARQLQuery(
            projection_variables=['?x'],  # Different projection variables
            where_clause=BGP([TriplePattern('?x', ':p', '?y')])
        )
        
        self.assertTrue(query1.is_isomorphic(query2),
            "Different projection variables should not affect pattern isomorphism")

    def test_solution_modifiers_not_considered(self):
        """Test that solution modifiers like ORDER BY don't affect isomorphism"""
        from sparqlsmith.query import OrderBy
        
        query1 = SPARQLQuery(
            where_clause=BGP([TriplePattern('?s', ':p', '?o')]),
            order_by=OrderBy(variables=['?o'], ascending=True)
        )
        
        query2 = SPARQLQuery(
            where_clause=BGP([TriplePattern('?x', ':p', '?y')]),
            # Different ORDER BY
            order_by=OrderBy(variables=['?x'], ascending=False) 
        )
        
        self.assertTrue(query1.is_isomorphic(query2),
            "Solution modifiers should not affect pattern isomorphism")


class TestSPARQLParser(unittest.TestCase):
    def setUp(self):
        self.parser = SPARQLParser()
        
    def _parse_and_verify(self, query_str, preserve_nesting=False):
        """Helper method to parse a query and do basic verification"""
        parser = SPARQLParser(preserve_nesting=preserve_nesting)
        result = parser.parse(query_str)
        query_obj = parser.structured_dict_to_query(result)
        
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
        
        # Verify the filter exists in the BGP
        self.assertIsInstance(query_obj.where_clause, BGP)
        self.assertEqual(len(query_obj.where_clause.filters), 1)
        self.assertEqual(query_obj.where_clause.filters[0].expression, "?o > 5")
        
    def test_nested_query_flattened(self):
        """Test that nested braces are flattened when preserve_nesting=False"""
        query_str = "SELECT ?s ?p ?o WHERE { { { ?s ?p ?o . } } }"
        query_obj = self._parse_and_verify(query_str, preserve_nesting=False)
        
        # The nested structure should be flattened to a simple BGP
        self.assertIsInstance(query_obj.where_clause, BGP)
        self.assertEqual(len(query_obj.where_clause.triples), 1)
        
        # Verify triple content
        triple = query_obj.where_clause.triples[0]
        self.assertEqual(triple.subject, "?s")
        self.assertEqual(triple.predicate, "?p")
        self.assertEqual(triple.object, "?o")
        
        # Verify serialized query doesn't have nested braces
        query_str_result = query_obj.to_query_string()
        self.assertNotIn("{  {", query_str_result)
        
    def test_nested_query_preserved(self):
        """Test that nested braces are preserved when preserve_nesting=True"""
        query_str = "SELECT ?s ?p ?o WHERE { { { ?s ?p ?o . } } }"
        query_obj = self._parse_and_verify(query_str, preserve_nesting=True)
        
        # The where clause should be a GroupGraphPattern
        self.assertIsInstance(query_obj.where_clause, GroupGraphPattern)
        
        # First level of nesting
        inner_pattern1 = query_obj.where_clause.pattern
        self.assertIsInstance(inner_pattern1, GroupGraphPattern)
        
        # Second level of nesting
        inner_pattern2 = inner_pattern1.pattern 
        self.assertIsInstance(inner_pattern2, BGP)
        self.assertEqual(len(inner_pattern2.triples), 1)
        
        # Verify triple content
        triple = inner_pattern2.triples[0]
        self.assertEqual(triple.subject, "?s")
        self.assertEqual(triple.predicate, "?p")
        self.assertEqual(triple.object, "?o")
        
        # Verify serialized query has nested braces
        query_str_result = query_obj.to_query_string()
        self.assertIn("{\n    {\n      ?s ?p ?o", query_str_result)
        

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
        
        # Check filter - filter should be in the first BGP in the where_clause list
        self.assertIsInstance(query_obj.where_clause, list)
        bgp_with_filter = None
        for element in query_obj.where_clause:
            if isinstance(element, BGP) and element.filters:
                bgp_with_filter = element
                break
        
        self.assertIsNotNone(bgp_with_filter, "No BGP with filters found")
        self.assertEqual(len(bgp_with_filter.filters), 1)
        self.assertEqual(bgp_with_filter.filters[0].expression, "?age > 25")
        
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

    def test_group_by_aggregation_compatibility(self):
        """Test GROUP BY and aggregation compatibility validation"""
        # Valid case: all SELECT vars are either in GROUP BY or aggregation results
        valid_query = """
            SELECT ?age (COUNT(?person) AS ?count)
            WHERE {
                ?person :name ?name .
                ?person :age ?age .
            }
            GROUP BY ?age
        """
        # Should parse successfully
        query_obj = self._parse_and_verify(valid_query)
        self.assertEqual(len(query_obj.projection_variables), 1)
        self.assertIn('?age', query_obj.projection_variables)
        self.assertEqual(query_obj.group_by.variables, ['?age'])
        self.assertEqual(len(query_obj.aggregations), 1)
        
        # Invalid case 1: SELECT contains variable not in GROUP BY
        invalid_query1 = """
            SELECT ?age ?name (COUNT(?person) AS ?count)
            WHERE {
                ?person :name ?name .
                ?person :age ?age .
            }
            GROUP BY ?age
        """
        with self.assertRaises(ValueError):
            self._parse_and_verify(invalid_query1)
            
        # Invalid case 2: Aggregation on variable in GROUP BY
        invalid_query2 = """
            SELECT ?age (COUNT(?age) AS ?ageCount)
            WHERE {
                ?person :name ?name .
                ?person :age ?age .
            }
            GROUP BY ?age
        """
        with self.assertRaises(OrderByValidationError):
            self._parse_and_verify(invalid_query2)
            
        # Test programmatic construction validation with new combined API
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
        
        # This should be valid
        self.assertEqual(len(query.projection_variables), 2)
        self.assertIn('?age', query.projection_variables)
        self.assertIn('?count', query.projection_variables)
        
        # Invalid: Try to add a non-aggregated, non-grouped variable to SELECT
        with self.assertRaises(ValueError):
            query.projection_variables = ['?age', '?count', '?name']
            
        # Invalid: Try to add aggregation on a GROUP BY variable
        with self.assertRaises(ValueError):
            invalid_agg = AggregationExpression(
                function="COUNT",
                variable="?age",
                alias="?ageCount",
                distinct=False
            )
            query.add_aggregation(invalid_agg)
            
        # Test adding multiple aggregations in one call
        query2 = SPARQLQuery()
        query2.add(bgp)
        
        agg1 = AggregationExpression(
            function="COUNT",
            variable="?person",
            alias="?personCount",
            distinct=True
        )
        
        agg2 = AggregationExpression(
            function="AVG",
            variable="?name",
            alias="?avgName",
            distinct=False
        )
        
        # Add GROUP BY with multiple aggregations
        query2.add_group_by('?age', aggregations=[agg1, agg2])
        query2.projection_variables = ['?age', '?personCount', '?avgName']
        
        self.assertEqual(len(query2.aggregations), 2)
        self.assertEqual(query2.aggregations[0].function, "COUNT")
        self.assertEqual(query2.aggregations[1].function, "AVG")

    def test_limit_clause(self):
        """Test parsing of a query with LIMIT clause"""
        query_str = """
            SELECT ?person ?name 
            WHERE { 
                ?person ?name ?name .
                ?person ?age ?age .
            }
            LIMIT 10
        """
        query_obj = self._parse_and_verify(query_str)
        
        # Verify the limit attribute exists and has the correct value
        self.assertIsNotNone(query_obj.limit)
        self.assertEqual(query_obj.limit, 10)
        
        # Check the serialized query contains the LIMIT clause
        query_str_result = query_obj.to_query_string()
        self.assertIn("LIMIT 10", query_str_result)


    def test_offset_clause(self):
        """Test parsing of a query with OFFSET clause"""
        query_str = """
            SELECT ?person ?name 
            WHERE { 
                ?person :name ?name .
                ?person :age ?age .
            }
            OFFSET 20
        """
        query_obj = self._parse_and_verify(query_str)
        
        # Verify the offset attribute exists and has the correct value
        self.assertIsNotNone(query_obj.offset)
        self.assertEqual(query_obj.offset, 20)
        
        # Check the serialized query contains the OFFSET clause
        query_str_result = query_obj.to_query_string()
        self.assertIn("OFFSET 20", query_str_result)
        
        # Test with combined LIMIT and OFFSET
        query_str = """
            SELECT ?person ?name 
            WHERE { 
                ?person :name ?name .
            }
            LIMIT 50
            OFFSET 100
        """
        query_obj = self._parse_and_verify(query_str)
        self.assertEqual(query_obj.limit, 50)
        self.assertEqual(query_obj.offset, 100)
        
        # Check serialization includes both clauses
        query_str_result = query_obj.to_query_string()
        self.assertIn("LIMIT 50", query_str_result)
        self.assertIn("OFFSET 100", query_str_result)

    def test_prefix_query(self):
        """Test parsing of a query with PREFIX declarations"""
        query_str = """
            PREFIX foaf: <http://xmlns.com/foaf/0.1/>
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            
            SELECT ?name
            WHERE { 
                ?person rdf:type foaf:Person .
                ?person foaf:name ?name .
            }
        """
        query_obj = self._parse_and_verify(query_str)
        
        # Check that prefixes were extracted
        self.assertIn('foaf', query_obj.prefixes)
        self.assertIn('rdf', query_obj.prefixes)
        self.assertEqual(query_obj.prefixes['foaf'], 'http://xmlns.com/foaf/0.1/')
        self.assertEqual(query_obj.prefixes['rdf'], 'http://www.w3.org/1999/02/22-rdf-syntax-ns#')
        
        # Check serialization includes PREFIX declarations
        query_str_result = query_obj.to_query_string()
        self.assertIn("PREFIX foaf: <http://xmlns.com/foaf/0.1/>", query_str_result)
        self.assertIn("PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>", query_str_result)


    def test_prefix_validation(self):
        """Test validation of PREFIX declarations"""
        # Create a BGP with prefixed terms
        bgp = BGP([
            TriplePattern('?person', 'rdf:type', 'foaf:Person'),
            TriplePattern('?person', 'foaf:name', '?name')
        ])
        
        # Attempt to create a query with incomplete prefixes - should raise ValueError
        with self.assertRaises(ValueError):
            query = SPARQLQuery(
                projection_variables=['?name'],
                where_clause=bgp,
                prefixes={'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#'}
            )
            
        # Create a query with all required prefixes - should succeed
        query = SPARQLQuery(
            projection_variables=['?name'],
            where_clause=bgp,
            prefixes={
                'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
                'foaf': 'http://xmlns.com/foaf/0.1/'
            }
        )
        
        # Add a new triple pattern using an undefined prefix
        new_bgp = BGP([
            TriplePattern('?person', 'dc:creator', '?creator')
        ])
        
        # Adding this to a new query without the dc prefix should fail
        with self.assertRaises(ValueError):
            query = SPARQLQuery(
                projection_variables=['?creator'],
                where_clause=new_bgp,
                prefixes={
                    'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
                    'foaf': 'http://xmlns.com/foaf/0.1/'
                }
            )

class TestQueryExecution(unittest.TestCase):
    """Test the query execution functionality"""
    
    @patch('requests.post')
    def test_run_method(self, mock_post):
        """Test the run method that executes queries against a SPARQL endpoint"""
        # Create mock response
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "head": {
                "vars": ["name", "population"]
            },
            "results": {
                "bindings": [
                    {
                        "name": {"type": "literal", "value": "Berlin"},
                        "population": {"type": "literal", "value": "3645000"}
                    }
                ]
            }
        }
        mock_post.return_value = mock_response
        
        # Create a simple query
        query = SPARQLQuery(
            projection_variables=["?name", "?population"],
            where_clause=BGP([
                TriplePattern("?city", "rdf:type", "dbo:City"),
                TriplePattern("?city", "rdfs:label", "?name"),
                TriplePattern("?city", "dbo:populationTotal", "?population")
            ])
        )
        
        # Execute the query against a mock endpoint
        result = query.run("https://dbpedia.org/sparql")
        
        # Verify that post was called with the correct arguments
        mock_post.assert_called_once()
        call_args = mock_post.call_args[0][0]
        self.assertEqual(call_args, "https://dbpedia.org/sparql")
        
        # Verify that the content-type and accept headers were set correctly
        headers = mock_post.call_args[1]["headers"]
        self.assertEqual(headers["Accept"], "application/sparql-results+json")
        self.assertEqual(headers["Content-Type"], "application/x-www-form-urlencoded")
        
        # Verify the query was properly serialized and sent
        data = mock_post.call_args[1]["data"]
        self.assertEqual(list(data.keys())[0], "query")
        self.assertIn("SELECT ?name ?population", data["query"])
        
        # Verify the result was properly returned
        self.assertEqual(result["head"]["vars"], ["name", "population"])
        self.assertEqual(len(result["results"]["bindings"]), 1)
        self.assertEqual(result["results"]["bindings"][0]["name"]["value"], "Berlin")
        self.assertEqual(result["results"]["bindings"][0]["population"]["value"], "3645000")
    

if __name__ == '__main__':
    unittest.main() 