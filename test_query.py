import unittest
from query import (
    SPARQLQuery,
    BGP,
    TriplePattern,
    UnionOperator,
    OptionalOperator,
    extract_triple_patterns
)

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

        # Negative example for simple BGP
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
            TriplePattern('?s1', ':p1', '?o5')
        ])
        query2 = SPARQLQuery(
            projection_variables=['?s', '?p', '?o'],
            where_clause=bgp2
        )

        self.assertFalse(query.is_isomorphic(query2))

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
        # First OPTIONAL
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

    def test_query_bgp_count(self):
        # Test for simple BGP
        bgp = BGP([
            TriplePattern('?s', ':p', '?o'),
            TriplePattern('?s', '?p2', '?o2')
        ])
        query = SPARQLQuery(
            projection_variables=['?s', '?p', '?o'],
            where_clause=bgp
        )

        self.assertEqual(query.count_bgps(), 1)

        # Test for UNION
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

        self.assertEqual(query.count_bgps(), 3)

        # Test for OPTIONAL
        main_bgp = BGP([
            TriplePattern('?s', '?p', '?o')
        ])
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

        self.assertEqual(query.count_bgps(), 2)

    def test_optional_query_string(self):
        # Main BGP
        main_bgp = BGP([
            TriplePattern('?s', '?p', '?o')
        ])

        # First OPTIONAL
        optional1 = OptionalOperator(
            bgp=BGP([
                TriplePattern('?s', '<http://example.org/predicate1>', '?optionalO1')
            ])
        )

        where_clause = [main_bgp, optional1]

        query = SPARQLQuery(
            projection_variables=['?s', '?p', '?o', '?optionalO1'],
            where_clause=where_clause
        )

        expected_query = """SELECT ?s ?p ?o ?optionalO1
WHERE {
  ?s ?p ?o .
  OPTIONAL {
    ?s <http://example.org/predicate1> ?optionalO1 .
  }
}"""
        self.assertEqual(query.to_query_string().strip(), expected_query.strip())

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


if __name__ == '__main__':
    unittest.main() 