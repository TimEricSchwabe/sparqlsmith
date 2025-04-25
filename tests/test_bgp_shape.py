import unittest
from sparqlsmith.query import TriplePattern, BGP

class TestBGPShape(unittest.TestCase):
    def test_single_triple(self):
        # Test a single triple pattern
        triple = TriplePattern(subject="?s", predicate="?p", object="?o")
        bgp = BGP([triple])
        self.assertEqual(bgp.shape(), "Single-triple")
    
    def test_path(self):
        # Test a path: ?s1 -> ?o1/s2 -> ?o2/s3 -> ?o3
        triples = [
            TriplePattern(subject="?s1", predicate="?p1", object="?o1"),
            TriplePattern(subject="?o1", predicate="?p2", object="?o2"),
            TriplePattern(subject="?o2", predicate="?p3", object="?o3")
        ]
        bgp = BGP(triples)
        self.assertEqual(bgp.shape(), "Path")
    
    def test_star(self):
        # Test a star: ?s is central with multiple outgoing edges
        triples = [
            TriplePattern(subject="?s", predicate="?p1", object="?o1"),
            TriplePattern(subject="?s", predicate="?p2", object="?o2"),
            TriplePattern(subject="?s", predicate="?p3", object="?o3"),
            TriplePattern(subject="?s", predicate="?p4", object="?o4")
        ]
        bgp = BGP(triples)
        self.assertEqual(bgp.shape(), "Star")
        
        # Test a star where ?o is central with multiple incoming edges
        triples = [
            TriplePattern(subject="?s1", predicate="?p1", object="?o"),
            TriplePattern(subject="?s2", predicate="?p2", object="?o"),
            TriplePattern(subject="?s3", predicate="?p3", object="?o"),
            TriplePattern(subject="?s4", predicate="?p4", object="?o")
        ]
        bgp = BGP(triples)
        self.assertEqual(bgp.shape(), "Star")
    
    def test_cycle(self):
        # Test a cycle: ?s1 -> ?o1/s2 -> ?o2/s3 -> ?s1
        triples = [
            TriplePattern(subject="?s1", predicate="?p1", object="?o1"),
            TriplePattern(subject="?o1", predicate="?p2", object="?o2"),
            TriplePattern(subject="?o2", predicate="?p3", object="?s1")
        ]
        bgp = BGP(triples)
        self.assertEqual(bgp.shape(), "Cycle")
    
    def test_tree(self):
        # Test a tree: hierarchical structure without cycles
        triples = [
            TriplePattern(subject="?root", predicate="?p1", object="?child1"),
            TriplePattern(subject="?root", predicate="?p2", object="?child2"),
            TriplePattern(subject="?child1", predicate="?p3", object="?grandchild1"),
            TriplePattern(subject="?child1", predicate="?p4", object="?grandchild2"),
            TriplePattern(subject="?child2", predicate="?p5", object="?grandchild3"),
            TriplePattern(subject="?child2", predicate="?p6", object="?grandchild4")
        ]
        bgp = BGP(triples)
        self.assertEqual(bgp.shape(), "Tree")
    
    def test_flower(self):
        # Test a flower: stem path with blooms at the end
        triples = [
            # Stem path
            TriplePattern(subject="?s1", predicate="?p1", object="?s2"),
            TriplePattern(subject="?s2", predicate="?p2", object="?s3"),
            TriplePattern(subject="?s3", predicate="?p3", object="?center"),
            # Blooms
            TriplePattern(subject="?center", predicate="?p4", object="?o1"),
            TriplePattern(subject="?center", predicate="?p5", object="?o2"),
            TriplePattern(subject="?center", predicate="?p6", object="?o3")
        ]
        bgp = BGP(triples)
        self.assertEqual(bgp.shape(), "Flower")
    
    def test_complex(self):
        # Test a complex shape with multiple cycles
        triples = [
            TriplePattern(subject="?s1", predicate="?p1", object="?o1"),
            TriplePattern(subject="?o1", predicate="?p2", object="?o2"),
            TriplePattern(subject="?o2", predicate="?p3", object="?s1"),
            TriplePattern(subject="?o2", predicate="?p4", object="?o3"),
            TriplePattern(subject="?o3", predicate="?p5", object="?o4"),
            TriplePattern(subject="?o4", predicate="?p6", object="?o2")
        ]
        bgp = BGP(triples)
        self.assertEqual(bgp.shape(), "Complex")

if __name__ == '__main__':
    unittest.main() 