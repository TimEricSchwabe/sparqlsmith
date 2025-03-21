from dataclasses import dataclass
from typing import List, Union, Dict, Optional, Set
import copy
import random
import re
import logging
from collections import defaultdict

# Configure logging
logging.basicConfig(level=logging.INFO)


@dataclass
class TriplePattern:
    """
    A class to represent a triple pattern in a SPARQL query.

    Attributes
    ----------
    subject : str
        The subject of the triple pattern.
    predicate : str
        The predicate of the triple pattern.
    object : str
        The object of the triple pattern.
    """
    subject: str
    predicate: str
    object: str


class BGP:
    """
    A class to represent a Basic Graph Pattern (BGP) in a SPARQL query.

    Attributes
    ----------
    triples : List[TriplePattern]
        A list of triple patterns that make up the BGP.
    """

    def __init__(self, triples: List[TriplePattern] = None):
        """
        Initialize a BGP object.

        Parameters
        ----------
        triples : List[TriplePattern], optional
            A list of triple patterns to initialize the BGP with (default is None).
        """
        self.triples = triples if triples is not None else []

    def add_triple_pattern(self, subject: str, predicate: str, object: str):
        """
        Add a triple pattern to the BGP.

        Parameters
        ----------
        subject : str
            The subject of the triple pattern.
        predicate : str
            The predicate of the triple pattern.
        object : str
            The object of the triple pattern.
        """
        triple = TriplePattern(subject, predicate, object)
        self.triples.append(triple)


@dataclass
class UnionOperator:
    left: Union['BGP', 'OptionalOperator', 'UnionOperator', 'SubQuery']
    right: Union['BGP', 'OptionalOperator', 'UnionOperator', 'SubQuery']


@dataclass
class OptionalOperator:
    """
    A class to represent an OPTIONAL pattern in a SPARQL query.

    Attributes
    ----------
    bgp : Union[BGP, UnionOperator, SubQuery]
        The graph pattern that is optionally matched.
    """
    bgp: Union['BGP', 'UnionOperator', 'SubQuery']


@dataclass
class Filter:
    expression: str


@dataclass
class OrderBy:
    variables: List[str]
    ascending: bool = True


@dataclass
class SubQuery:
    query: 'SPARQLQuery'


class SPARQLQuery:
    def __init__(
            self,
            projection_variables: List[str] = None,
            where_clause: Union[BGP, UnionOperator, OptionalOperator, SubQuery, List[SubQuery]] = None,
            filters: List[Filter] = None,
            order_by: Optional[OrderBy] = None,
            limit: Optional[int] = None,
            offset: Optional[int] = None,
            graph: Optional[str] = None,
            is_count_query: bool = False
    ):

        self.projection_variables = projection_variables if projection_variables is not None else ['*']
        self.where_clause = where_clause
        self.filters = filters
        self.order_by = order_by
        self.limit = limit
        self.offset = offset
        self.graph = graph
        self.is_count_query = is_count_query
        self.n_triple_patterns = self._count_triple_patterns(where_clause)

    def instantiate(self, mapping_dict: Dict[str, str]) -> 'SPARQLQuery':
        """
        Instantiate variables in the query using the provided mapping dictionary.

        This method modifies the TriplePattern objects in-place and removes instantiated variables
        from the projection variables list.

        Parameters
        ----------
        mapping_dict : Dict[str, str]
            A dictionary mapping variable names to their values.

        Returns
        -------
        SPARQLQuery
            The query with instantiated variables and adjusted projection variables.
        """
        self._instantiate_clause(self.where_clause, mapping_dict)

        # After instantiation, remove instantiated variables from projection variables
        if self.projection_variables != ['*']:
            # Keep only variables that were not instantiated
            self.projection_variables = [
                var for var in self.projection_variables 
                if var.startswith('?') and var[1:] not in mapping_dict
            ]
            
            # If all projection variables were instantiated, get all remaining variables
            if not self.projection_variables:
                self.projection_variables = list(self.get_all_variables())

        return self

    def get_all_variables(self) -> Set[str]:
        """
        Collect all variables in the query's WHERE clause.

        Returns
        -------
        Set[str]
            A set of variable names (including the '?' prefix).
        """
        variables = set()
        self._collect_variables(self.where_clause, variables)
        return variables

    def _collect_variables(
            self,
            clause: Union[BGP, UnionOperator, OptionalOperator, SubQuery, List[SubQuery]],
            variables: Set[str]
    ):
        if isinstance(clause, BGP):
            for triple in clause.triples:
                for term in [triple.subject, triple.predicate, triple.object]:
                    if term.startswith('?'):
                        variables.add(term)
        elif isinstance(clause, UnionOperator):
            self._collect_variables(clause.left, variables)
            self._collect_variables(clause.right, variables)
        elif isinstance(clause, OptionalOperator):
            self._collect_variables(clause.bgp, variables)
        elif isinstance(clause, SubQuery):
            variables.update(clause.query.get_all_variables())
        elif isinstance(clause, list):
            for subquery in clause:
                self._collect_variables(subquery, variables)
        # Filters might contain variables as well
        if hasattr(clause, 'expression') and isinstance(clause.expression, str):
            for word in clause.expression.split():
                if word.startswith('?'):
                    variables.add(word)

    def _instantiate_clause(
            self,
            clause: Union[BGP, UnionOperator, OptionalOperator, SubQuery, List[SubQuery]],
            mapping_dict: Dict[str, str]
    ):
        if isinstance(clause, BGP):
            for triple in clause.triples:
                triple.subject = self._replace_variable(triple.subject, mapping_dict)
                triple.predicate = self._replace_variable(triple.predicate, mapping_dict)
                triple.object = self._replace_variable(triple.object, mapping_dict)
        elif isinstance(clause, UnionOperator):
            self._instantiate_clause(clause.left, mapping_dict)
            self._instantiate_clause(clause.right, mapping_dict)
        elif isinstance(clause, OptionalOperator):
            self._instantiate_clause(clause.bgp, mapping_dict)
        elif isinstance(clause, SubQuery):
            clause.query.instantiate(mapping_dict)
        elif isinstance(clause, list):
            for item in clause:
                self._instantiate_clause(item, mapping_dict)

    def _replace_variable(self, value: str, mapping_dict: Dict[str, str]) -> str:
        if value.startswith('?'):
            var_name = value[1:]
            if var_name in mapping_dict:
                return f"<{mapping_dict[var_name]}>"
        return value

    def copy(self, **kwargs) -> 'SPARQLQuery':
        """
        Create a copy of the current query with optional attribute overrides.

        Parameters
        ----------
        kwargs : dict
            A dictionary of attribute names and their new values.

        Returns
        -------
        SPARQLQuery
            A new SPARQLQuery object with the specified attribute overrides.
        """
        new_query = copy.deepcopy(self)
        for key, value in kwargs.items():
            if hasattr(new_query, key):
                setattr(new_query, key, value)
            else:
                raise AttributeError(f"'SPARQLQuery' object has no attribute '{key}'")
        return new_query

    def to_query_string(self) -> str:
        """
        Convert the SPARQLQuery object to a SPARQL query string.

        Returns
        -------
        str
            The SPARQL query string.
        """
        if self.is_count_query:
            query = "SELECT (COUNT(*) AS ?count)\n"
        else:
            query = f"SELECT {' '.join(self.projection_variables)}\n"
        if self.graph:
            query += f"FROM <{self.graph}>\n"
        query += "WHERE {\n"
        query += self._serialize_where_clause(self.where_clause, 1)
        if self.filters:
            for filter in self.filters:
                query += f"  FILTER({filter.expression})\n"
        query += "}"
        if self.order_by:
            direction = "ASC" if self.order_by.ascending else "DESC"
            query += f"\nORDER BY {direction}({' '.join(self.order_by.variables)})"
        if self.limit is not None:
            query += f"\nLIMIT {self.limit}"
        if self.offset is not None:
            query += f"\nOFFSET {self.offset}"
        return query

    def _serialize_where_clause(
            self,
            clause: Union[BGP, UnionOperator, OptionalOperator, SubQuery, List[
                Union['BGP', 'UnionOperator', 'OptionalOperator', 'SubQuery']]],
            indent: int
    ) -> str:
        if isinstance(clause, BGP):
            return self._serialize_bgp(clause, indent)
        elif isinstance(clause, UnionOperator):
            return self._serialize_union(clause, indent)
        elif isinstance(clause, OptionalOperator):
            return self._serialize_optional(clause, indent)
        elif isinstance(clause, SubQuery):
            return self._serialize_subquery(clause, indent)
        elif isinstance(clause, list):
            return ''.join(self._serialize_where_clause(sq, indent) for sq in clause)
        else:
            raise ValueError(f"Unknown clause type: {type(clause)}")

    def _serialize_bgp(self, bgp: BGP, indent: int) -> str:
        result = ""
        for triple in bgp.triples:
            result += "  " * indent + f"{triple.subject} {triple.predicate} {triple.object} .\n"
        return result

    def _serialize_union(self, union: UnionOperator, indent: int) -> str:
        return (
                "  " * indent + "{\n" +
                self._serialize_where_clause(union.left, indent + 1) +
                "  " * indent + "} UNION {\n" +
                self._serialize_where_clause(union.right, indent + 1) +
                "  " * indent + "}\n"
        )

    def _serialize_optional(self, optional: OptionalOperator, indent: int) -> str:
        return (
                "  " * indent + "OPTIONAL {\n" +
                self._serialize_where_clause(optional.bgp, indent + 1) +
                "  " * indent + "}\n"
        )

    def _serialize_subquery(self, subquery: SubQuery, indent: int) -> str:
        subquery_str = subquery.query.to_query_string()
        indented_subquery = '\n'.join("  " * indent + line for line in subquery_str.split('\n'))
        return f"{'  ' * indent}{{\n{indented_subquery}\n{'  ' * indent}}}\n"

    def replace_triple_patterns_with_subqueries(self, limit: int = 300) -> 'SPARQLQuery':
        new_query = copy.deepcopy(self)
        new_query.where_clause = self._replace_clause(new_query.where_clause, limit)
        return new_query

    def _replace_clause(
            self,
            clause: Union[BGP, UnionOperator, OptionalOperator, SubQuery, List[SubQuery]],
            limit: int
    ) -> Union[BGP, UnionOperator, OptionalOperator, SubQuery, List[SubQuery]]:
        if isinstance(clause, BGP):
            return self._replace_bgp(clause, limit)
        elif isinstance(clause, UnionOperator):
            clause.left = self._replace_clause(clause.left, limit)
            clause.right = self._replace_clause(clause.right, limit)
            return clause
        elif isinstance(clause, OptionalOperator):
            clause.bgp = self._replace_clause(clause.bgp, limit)
            return clause
        elif isinstance(clause, SubQuery):
            clause.query = clause.query.replace_triple_patterns_with_subqueries(limit)
            return clause
        elif isinstance(clause, list):
            return [self._replace_clause(sq, limit) for sq in clause]
        else:
            raise ValueError(f"Unknown clause type: {type(clause)}")

    def _replace_bgp(self, bgp: BGP, limit: int) -> Union[BGP, List[SubQuery]]:
        if not bgp.triples:
            return bgp

        subqueries = []
        for triple in bgp.triples:
            subquery = SPARQLQuery(
                projection_variables=["*"],
                where_clause=BGP([triple]),
                limit=limit
            )
            subqueries.append(SubQuery(subquery))

        return subqueries

    def _count_triple_patterns(
            self,
            clause: Union[BGP, UnionOperator, OptionalOperator, SubQuery, List[SubQuery]]
    ) -> int:
        if isinstance(clause, BGP):
            return len(clause.triples)
        elif isinstance(clause, UnionOperator):
            return self._count_triple_patterns(clause.left) + self._count_triple_patterns(clause.right)
        elif isinstance(clause, OptionalOperator):
            return self._count_triple_patterns(clause.bgp)
        elif isinstance(clause, SubQuery):
            return clause.query.n_triple_patterns
        elif isinstance(clause, list):
            return sum(self._count_triple_patterns(sq) for sq in clause)
        else:
            return 0

    def count_bgps(self) -> int:
        """
        Count the number of Basic Graph Patterns (BGPs) in the query.

        Returns
        -------
        int
            The number of BGPs.
        """
        return self._count_bgps_recursive(self.where_clause)

    def _count_bgps_recursive(
            self,
            clause: Union[BGP, UnionOperator, OptionalOperator, SubQuery, List[SubQuery]]
    ) -> int:
        if isinstance(clause, BGP):
            return 1
        elif isinstance(clause, UnionOperator):
            return self._count_bgps_recursive(clause.left) + self._count_bgps_recursive(clause.right)
        elif isinstance(clause, OptionalOperator):
            return self._count_bgps_recursive(clause.bgp)
        elif isinstance(clause, SubQuery):
            return clause.query.count_bgps()
        elif isinstance(clause, list):
            return sum(self._count_bgps_recursive(subquery) for subquery in clause)
        else:
            return 0

    def is_isomorphic(self, other: 'SPARQLQuery') -> bool:
        """
        Check if this SPARQLQuery is isomorphic to another, considering variable renaming
        and structural equivalence.

        Parameters
        ----------
        other : SPARQLQuery
            The other query to compare against.

        Returns
        -------
        bool
            True if the queries are isomorphic, False otherwise.
        """
        variable_mapping = {}
        return self._compare_clauses(self.where_clause, other.where_clause, variable_mapping)

    def _compare_clauses(self, clause1, clause2, variable_mapping) -> bool:
        if type(clause1) != type(clause2):
            return False

        elif isinstance(clause1, BGP):
            return self._compare_bgps(clause1, clause2, variable_mapping)

        elif isinstance(clause1, UnionOperator):
            return self._compare_unions(clause1, clause2, variable_mapping)

        elif isinstance(clause1, OptionalOperator):
            return self._compare_optionals(clause1, clause2, variable_mapping)

        elif isinstance(clause1, SubQuery):
            return clause1.query.is_isomorphic(clause2.query)

        elif isinstance(clause1, list):
            if len(clause1) != len(clause2):
                return False
            for sub1, sub2 in zip(clause1, clause2):
                if not self._compare_clauses(sub1, sub2, variable_mapping):
                    return False
            return True

        else:
            return False

    def _compare_bgps(self, bgp1: BGP, bgp2: BGP, variable_mapping) -> bool:
        if len(bgp1.triples) != len(bgp2.triples):
            return False

        # Attempt to match triple patterns
        used_indices = set()

        def match_triples(index1, mapping):
            if index1 == len(bgp1.triples):
                return True  # All triples matched

            tp1 = bgp1.triples[index1]

            for index2 in range(len(bgp2.triples)):
                if index2 in used_indices:
                    continue

                tp2 = bgp2.triples[index2]

                # Try to match tp1 and tp2 under current variable mapping
                new_mapping = mapping.copy()
                if self._compare_triple_patterns(tp1, tp2, new_mapping):
                    # Triple patterns match, update variable mapping and proceed
                    used_indices.add(index2)
                    if match_triples(index1 + 1, new_mapping):
                        # Found a complete match
                        mapping.update(new_mapping)
                        return True
                    # Backtrack
                    used_indices.remove(index2)
            return False  # No match found

        return match_triples(0, variable_mapping)

    def _compare_triple_patterns(self, tp1: TriplePattern, tp2: TriplePattern, variable_mapping) -> bool:
        return (
                self._compare_terms(tp1.subject, tp2.subject, variable_mapping) and
                self._compare_terms(tp1.predicate, tp2.predicate, variable_mapping) and
                self._compare_terms(tp1.object, tp2.object, variable_mapping)
        )

    def _compare_terms(self, term1: str, term2: str, variable_mapping) -> bool:
        if term1.startswith('?') and term2.startswith('?'):
            var1 = term1[1:]
            var2 = term2[1:]

            if var1 in variable_mapping:
                return variable_mapping[var1] == var2
            else:
                if var2 in variable_mapping.values():
                    return False  # var2 is already mapped to a different variable
                variable_mapping[var1] = var2
                return True

        else:
            return term1 == term2

    def _compare_unions(self, union1: UnionOperator, union2: UnionOperator, variable_mapping) -> bool:
        # Since UNION is commutative, consider both possibilities
        mapping_copy = variable_mapping.copy()
        if (self._compare_clauses(union1.left, union2.left, mapping_copy) and
                self._compare_clauses(union1.right, union2.right, mapping_copy)):
            variable_mapping.update(mapping_copy)
            return True

        mapping_copy = variable_mapping.copy()
        if (self._compare_clauses(union1.left, union2.right, mapping_copy) and
                self._compare_clauses(union1.right, union2.left, mapping_copy)):
            variable_mapping.update(mapping_copy)
            return True

        return False

    def _compare_optionals(self, opt1: OptionalOperator, opt2: OptionalOperator, variable_mapping) -> bool:
        return self._compare_clauses(opt1.bgp, opt2.bgp, variable_mapping)


def extract_triple_patterns(sparql_query: SPARQLQuery) -> List[TriplePattern]:
    """
    Extract all triple patterns from the SPARQLQuery object.

    Parameters
    ----------
    sparql_query : SPARQLQuery
        The SPARQL query object.

    Returns
    -------
    List[TriplePattern]
        A list of TriplePattern objects.
    """
    triples = []
    _extract_triples_recursive(sparql_query.where_clause, triples)
    return triples


def _extract_triples_recursive(
    clause: Union[BGP, UnionOperator, OptionalOperator, SubQuery, List[SubQuery]],
    triples: List[TriplePattern]
):
    if isinstance(clause, BGP):
        triples.extend(clause.triples)
    elif isinstance(clause, UnionOperator):
        _extract_triples_recursive(clause.left, triples)
        _extract_triples_recursive(clause.right, triples)
    elif isinstance(clause, OptionalOperator):
        _extract_triples_recursive(clause.bgp, triples)
    elif isinstance(clause, SubQuery):
        _extract_triples_recursive(clause.query.where_clause, triples)
    elif isinstance(clause, list):
        for subquery in clause:
            _extract_triples_recursive(subquery, triples)


def check_if_triple_all_variables(triple: TriplePattern) -> bool:
    """
    Check if all parts of the triple are variables.

    Args:
        triple (TriplePattern): The triple pattern to check.

    Returns:
        bool: True if all parts are variables, False otherwise.
    """
    return all(part.startswith('?') for part in [triple.subject, triple.predicate, triple.object])


def get_combined_query(prefix: str, triples: List[TriplePattern]) -> str:
    """
    Combine prefix and triple patterns into a SPARQL query string.

    Args:
        prefix (str): The PREFIX declarations.
        triples (List[TriplePattern]): The list of triple patterns.

    Returns:
        str: The combined SPARQL query string.
    """
    query = f"{prefix}\nSELECT (COUNT(*) AS ?count)\nWHERE {{\n"
    for triple in triples:
        query += f"  {triple.subject} {triple.predicate} {triple.object} .\n"
    query += "}"
    return query 