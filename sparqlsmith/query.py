from dataclasses import dataclass, field
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
    _parent: 'BGP' = None  # Reference to parent BGP
    
    def remove(self):
        """
        Remove this triple pattern from its parent BGP.
        
        Returns
        -------
        bool
            True if removal was successful, False otherwise.
        """
        if self._parent is not None and self in self._parent.triples:
            self._parent.triples.remove(self)
            return True
        return False


class BGP:
    """
    A class to represent a Basic Graph Pattern (BGP) in a SPARQL query.

    Attributes
    ----------
    triples : List[TriplePattern]
        A list of triple patterns that make up the BGP.
    filters : List['Filter']
        A list of filters that apply to this BGP.
    """

    def __init__(self, triples: List[TriplePattern] = None, filters: List['Filter'] = None):
        """
        Initialize a BGP object.

        Parameters
        ----------
        triples : List[TriplePattern], optional
            A list of triple patterns to initialize the BGP with (default is None).
        filters : List['Filter'], optional
            A list of filters to initialize the BGP with (default is None).
        """
        self.triples = triples if triples is not None else []
        # Set parent reference for each triple
        for triple in self.triples:
            triple._parent = self
            
        self.filters = filters if filters is not None else []
        # Set parent reference for each filter
        for filter in self.filters:
            filter._parent = self
            
        self._parent = None  # Reference to parent query or operator
    
    def add(self, component):
        """
        Add a component (TriplePattern or Filter) to this BGP.
        
        Parameters
        ----------
        component : Union[TriplePattern, Filter, str, tuple]
            Component to add. Can be:
            - TriplePattern: directly added to triples
            - Filter: directly added to filters
            - tuple of (subject, predicate, object): converted to TriplePattern
            - str: interpreted as a filter expression
            
        Returns
        -------
        The added component object
        
        Raises
        ------
        TypeError
            If the component is not a valid type
        """
        # Handle tuple case (s, p, o)
        if isinstance(component, tuple) and len(component) == 3:
            triple = TriplePattern(subject=component[0], predicate=component[1], object=component[2])
            triple._parent = self
            self.triples.append(triple)
            return triple
            
        # Handle TriplePattern case
        elif isinstance(component, TriplePattern):
            component._parent = self
            self.triples.append(component)
            return component
            
        # Handle Filter case
        elif isinstance(component, Filter):
            component._parent = self
            self.filters.append(component)
            return component
            
        # Handle string case (filter expression)
        elif isinstance(component, str):
            filter = Filter(expression=component)
            filter._parent = self
            self.filters.append(filter)
            return filter
            
        else:
            raise TypeError(f"Cannot add component of type {type(component)} to BGP")
        
    def remove(self):
        """
        Remove this BGP from its parent container (query or operator).
        
        Returns
        -------
        bool
            True if removal was successful, False otherwise.
        """
        if self._parent is None:
            return False
            
        if isinstance(self._parent, SPARQLQuery):
            if self._parent.where_clause == self:
                self._parent.where_clause = None
                return True
            elif isinstance(self._parent.where_clause, list) and self in self._parent.where_clause:
                self._parent.where_clause.remove(self)
                return True
        elif isinstance(self._parent, OptionalOperator):
            if self._parent.bgp == self:
                self._parent.bgp = None
                self._parent.remove()  # Remove the optional operator as it's no longer valid
                return True
        elif isinstance(self._parent, (UnionOperator, GroupGraphPattern)):
            if self._parent.left == self:
                self._parent.left = None
                self._parent.remove()  # Remove the union/group as it's no longer valid
                return True
            elif self._parent.right == self:
                self._parent.right = None
                self._parent.remove()  # Remove the union/group as it's no longer valid
                return True
                
        return False


@dataclass
class UnionOperator:
    left: Union['BGP', 'OptionalOperator', 'UnionOperator', 'SubQuery']
    right: Union['BGP', 'OptionalOperator', 'UnionOperator', 'SubQuery']
    _parent = None  # Reference to parent container
    
    def __post_init__(self):
        # Set parent references
        if hasattr(self.left, '_parent'):
            self.left._parent = self
        if hasattr(self.right, '_parent'):
            self.right._parent = self
            
    def remove(self):
        """
        Remove this union operator from its parent container.
        
        Returns
        -------
        bool
            True if removal was successful, False otherwise.
        """
        if self._parent is None:
            return False
            
        if isinstance(self._parent, SPARQLQuery):
            if self._parent.where_clause == self:
                self._parent.where_clause = None
                return True
            elif isinstance(self._parent.where_clause, list) and self in self._parent.where_clause:
                self._parent.where_clause.remove(self)
                return True
        elif isinstance(self._parent, GroupGraphPattern):
            if self._parent.pattern == self:
                self._parent.pattern = None
                self._parent.remove()  # Remove the group as it's no longer valid
                return True
                
        return False


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
    _parent = None  # Reference to parent container
    
    def __post_init__(self):
        # Set parent reference
        if hasattr(self.bgp, '_parent'):
            self.bgp._parent = self
            
    def remove(self):
        """
        Remove this optional operator from its parent container.
        
        Returns
        -------
        bool
            True if removal was successful, False otherwise.
        """
        if self._parent is None:
            return False
            
        if isinstance(self._parent, SPARQLQuery):
            if self._parent.where_clause == self:
                self._parent.where_clause = None
                return True
            elif isinstance(self._parent.where_clause, list) and self in self._parent.where_clause:
                self._parent.where_clause.remove(self)
                return True
        elif isinstance(self._parent, GroupGraphPattern):
            if self._parent.pattern == self:
                self._parent.pattern = None
                self._parent.remove()  # Remove the group as it's no longer valid
                return True
                
        return False


@dataclass
class Filter:
    expression: str
    _parent = None  # Reference to parent BGP or query
    
    def remove(self):
        """
        Remove this filter from its parent container.
        
        Returns
        -------
        bool
            True if removal was successful, False otherwise.
        """
        if self._parent is None:
            return False
            
        if isinstance(self._parent, BGP):
            if self in self._parent.filters:
                self._parent.filters.remove(self)
                return True
        elif isinstance(self._parent, SPARQLQuery):
            if self._parent.filters and self in self._parent.filters:
                self._parent.filters.remove(self)
                return True
        elif isinstance(self._parent, GroupGraphPattern):
            if self in self._parent.filters:
                self._parent.filters.remove(self)
                return True
                
        return False


@dataclass
class Having:
    """
    A class to represent a HAVING condition in a SPARQL query.
    
    Attributes
    ----------
    expression : str
        The expression to filter groups after aggregation.
    """
    expression: str
    _parent = None  # Reference to parent query
    
    def remove(self):
        """
        Remove this HAVING condition from its parent query.
        
        Returns
        -------
        bool
            True if removal was successful, False otherwise.
        """
        if self._parent is None:
            return False
            
        if isinstance(self._parent, SPARQLQuery):
            if self._parent.having and self in self._parent.having:
                self._parent.having.remove(self)
                return True
                
        return False


@dataclass
class OrderBy:
    variables: List[str]
    ascending: Union[bool, List[bool]] = True
    _parent = None  # Reference to parent query
    
    def add(self, variable, ascending=True):
        """
        Add a variable to the ORDER BY clause.
        
        Parameters
        ----------
        variable : str
            The variable to add for ordering
        ascending : bool, optional
            Whether to sort in ascending order (default is True)
            
        Returns
        -------
        self
            For method chaining
        """
        self.variables.append(variable)
        
        # Handle the ascending flag
        if isinstance(self.ascending, bool):
            # Convert to list if it was a single boolean
            if len(self.variables) > 1:
                self.ascending = [self.ascending] * (len(self.variables) - 1)
                self.ascending.append(ascending)
        else:
            # Already a list, just append
            self.ascending.append(ascending)
            
        return self
    
    def remove(self):
        """
        Remove this ORDER BY clause from its parent query.
        
        Returns
        -------
        bool
            True if removal was successful, False otherwise.
        """
        if self._parent is None:
            return False
            
        if isinstance(self._parent, SPARQLQuery):
            if self._parent.order_by == self:
                self._parent.order_by = None
                return True
                
        return False


@dataclass
class GroupBy:
    variables: List[str]
    _parent = None  # Reference to parent query
    
    def add(self, variable):
        """
        Add a variable to the GROUP BY clause.
        
        Parameters
        ----------
        variable : str
            The variable to add for grouping
            
        Returns
        -------
        self
            For method chaining
        """
        if variable not in self.variables:
            self.variables.append(variable)
        return self
    
    def remove(self):
        """
        Remove this GROUP BY clause from its parent query.
        
        Returns
        -------
        bool
            True if removal was successful, False otherwise.
        """
        if self._parent is None:
            return False
            
        if isinstance(self._parent, SPARQLQuery):
            if self._parent.group_by == self:
                self._parent.group_by = None
                return True
                
        return False


@dataclass
class SubQuery:
    query: 'SPARQLQuery'
    _parent = None  # Reference to parent container
    
    def __post_init__(self):
        self.query._parent = self
    
    def add(self, component):
        """
        Add a component to the subquery's where clause.
        
        Parameters
        ----------
        component : Union[BGP, UnionOperator, OptionalOperator, GroupGraphPattern, Filter]
            The component to add to the subquery
            
        Returns
        -------
        The added component
        """
        return self.query.add(component)
        
    def remove(self):
        """
        Remove this subquery from its parent container.
        
        Returns
        -------
        bool
            True if removal was successful, False otherwise.
        """
        if self._parent is None:
            return False
            
        if isinstance(self._parent, SPARQLQuery):
            if self._parent.where_clause == self:
                self._parent.where_clause = None
                return True
            elif isinstance(self._parent.where_clause, list) and self in self._parent.where_clause:
                self._parent.where_clause.remove(self)
                return True
        elif isinstance(self._parent, OptionalOperator):
            if self._parent.bgp == self:
                self._parent.bgp = None
                self._parent.remove()  # Remove the optional operator as it's no longer valid
                return True
        elif isinstance(self._parent, UnionOperator):
            if self._parent.left == self:
                self._parent.left = None
                self._parent.remove()  # Remove the union as it's no longer valid
                return True
            elif self._parent.right == self:
                self._parent.right = None
                self._parent.remove()  # Remove the union as it's no longer valid
                return True
        elif isinstance(self._parent, GroupGraphPattern):
            if self._parent.pattern == self:
                self._parent.pattern = None
                self._parent.remove()  # Remove the group as it's no longer valid
                return True
                
        return False


@dataclass
class GroupGraphPattern:
    """
    A class to represent a nested group graph pattern in a SPARQL query.

    Attributes
    ----------
    pattern : Union[BGP, UnionOperator, OptionalOperator, SubQuery, 'GroupGraphPattern']
        The contained pattern inside the group.
    filters : List['Filter']
        A list of filters that apply to this group pattern.
    """
    pattern: Union['BGP', 'UnionOperator', 'OptionalOperator', 'SubQuery', 'GroupGraphPattern']
    filters: List['Filter'] = field(default_factory=list)
    _parent = None  # Reference to parent container
    
    def __post_init__(self):
        # Set parent references
        if hasattr(self.pattern, '_parent'):
            self.pattern._parent = self
        for filter in self.filters:
            filter._parent = self
    
    def add(self, component):
        """
        Add a component to this group graph pattern.
        
        Parameters
        ----------
        component : Union[BGP, UnionOperator, OptionalOperator, SubQuery, GroupGraphPattern, Filter, str]
            The component to add. If a string, it will be treated as a filter expression.
            
        Returns
        -------
        The added component
        
        Raises
        ------
        TypeError
            If the component is not a valid type or if trying to add a pattern when one already exists
        """
        # Handle filter case
        if isinstance(component, Filter):
            component._parent = self
            self.filters.append(component)
            return component
            
        # Handle filter expression string
        elif isinstance(component, str):
            filter = Filter(expression=component)
            filter._parent = self
            self.filters.append(filter)
            return filter
            
        # Handle pattern case
        elif isinstance(component, (BGP, UnionOperator, OptionalOperator, SubQuery, GroupGraphPattern)):
            if self.pattern is not None:
                raise TypeError("GroupGraphPattern already has a pattern. Cannot add another one.")
            self.pattern = component
            component._parent = self
            return component
            
        else:
            raise TypeError(f"Cannot add component of type {type(component)} to GroupGraphPattern")
            
    def remove(self):
        """
        Remove this group graph pattern from its parent container.
        
        Returns
        -------
        bool
            True if removal was successful, False otherwise.
        """
        if self._parent is None:
            return False
            
        if isinstance(self._parent, SPARQLQuery):
            if self._parent.where_clause == self:
                self._parent.where_clause = None
                return True
            elif isinstance(self._parent.where_clause, list) and self in self._parent.where_clause:
                self._parent.where_clause.remove(self)
                return True
        elif isinstance(self._parent, GroupGraphPattern):
            if self._parent.pattern == self:
                self._parent.pattern = None
                return True
                
        return False


@dataclass
class AggregationExpression:
    """
    A class to represent an aggregation expression in a SPARQL query.
    
    Attributes
    ----------
    function : str
        The aggregation function (COUNT, SUM, MIN, MAX, AVG)
    variable : str
        The variable or expression to aggregate
    alias : str
        The variable name assigned to the result (after AS)
    distinct : bool
        Whether the DISTINCT keyword is used in the aggregation
    """
    function: str  # COUNT, SUM, MIN, MAX, AVG
    variable: str  # Variable or expression to aggregate
    alias: str     # Result variable name (after AS)
    distinct: bool = False
    _parent = None  # Reference to parent query
    
    def remove(self):
        """
        Remove this aggregation expression from its parent query.
        
        Returns
        -------
        bool
            True if removal was successful, False otherwise.
        """
        if self._parent is None:
            return False
            
        if isinstance(self._parent, SPARQLQuery):
            if self in self._parent.aggregations:
                self._parent.aggregations.remove(self)
                return True
                
        return False


class SPARQLQuery:
    def __init__(
            self,
            projection_variables: List[str] = None,
            where_clause: Union[BGP, UnionOperator, OptionalOperator, SubQuery, List[SubQuery]] = None,
            filters: List[Filter] = None,
            having: List[Having] = None,
            order_by: Optional[OrderBy] = None,
            group_by: Optional[GroupBy] = None,
            limit: Optional[int] = None,
            offset: Optional[int] = None,
            graph: Optional[str] = None,
            is_distinct: bool = False,
            aggregations: List[AggregationExpression] = None
    ):

        self.projection_variables = projection_variables if projection_variables is not None else ['*']
        self.where_clause = where_clause
        # Set parent reference for each component in where_clause
        self._set_parent_references(where_clause)
        
        self.filters = filters
        # Set parent reference for each filter
        if self.filters:
            for filter in self.filters:
                filter._parent = self
                
        self.having = having
        # Set parent reference for each having condition
        if self.having:
            for having_cond in self.having:
                having_cond._parent = self
                
        self.order_by = order_by
        if self.order_by:
            self.order_by._parent = self
            
        self.group_by = group_by
        if self.group_by:
            self.group_by._parent = self
            
        self.limit = limit
        self.offset = offset
        self.graph = graph
        self.is_distinct = is_distinct
        
        self.aggregations = aggregations if aggregations is not None else []
        # Set parent reference for each aggregation
        for agg in self.aggregations:
            agg._parent = self
            
        self.n_triple_patterns = self._count_triple_patterns(where_clause)
        self._parent = None  # Reference to parent (for subqueries)

    def _set_parent_references(self, clause):
        """Set parent references for components in the where clause."""
        if isinstance(clause, (BGP, UnionOperator, OptionalOperator, SubQuery, GroupGraphPattern)):
            clause._parent = self
            
            # Recursively set parent references for nested components
            if isinstance(clause, BGP):
                for triple in clause.triples:
                    triple._parent = clause
                for filter in clause.filters:
                    filter._parent = clause
            elif isinstance(clause, UnionOperator):
                self._set_parent_references(clause.left)
                self._set_parent_references(clause.right)
            elif isinstance(clause, OptionalOperator):
                self._set_parent_references(clause.bgp)
            elif isinstance(clause, SubQuery):
                clause.query._parent = clause
            elif isinstance(clause, GroupGraphPattern):
                self._set_parent_references(clause.pattern)
                for filter in clause.filters:
                    filter._parent = clause
        elif isinstance(clause, list):
            for item in clause:
                self._set_parent_references(item)
    
    def add(self, component):
        """
        Add a component to the query's WHERE clause.
        
        Parameters
        ----------
        component : Union[BGP, UnionOperator, OptionalOperator, SubQuery, GroupGraphPattern, Filter, str]
            The component to add. If a string, it will be treated as a filter expression.
            
        Returns
        -------
        The added component
        
        Raises
        ------
        TypeError
            If the component is not a valid type
        """
        # Handle filter case
        if isinstance(component, Filter):
            if self.filters is None:
                self.filters = []
            component._parent = self
            self.filters.append(component)
            return component
            
        # Handle filter expression string
        elif isinstance(component, str) and not isinstance(component, (BGP, UnionOperator, OptionalOperator, SubQuery, GroupGraphPattern)):
            filter = Filter(expression=component)
            if self.filters is None:
                self.filters = []
            filter._parent = self
            self.filters.append(filter)
            return filter
            
        # Handle other components for where_clause
        elif isinstance(component, (BGP, UnionOperator, OptionalOperator, SubQuery, GroupGraphPattern)):
            if self.where_clause is None:
                self.where_clause = component
                component._parent = self
            elif isinstance(self.where_clause, list):
                self.where_clause.append(component)
                component._parent = self
            else:
                # Convert to list if it's not already one
                self.where_clause = [self.where_clause, component]
                component._parent = self
                
            # Update triple pattern count
            self.n_triple_patterns = self._count_triple_patterns(self.where_clause)
            return component
            
        else:
            raise TypeError(f"Cannot add component of type {type(component)} to SPARQLQuery")
    
    def add_having(self, expression):
        """
        Add a HAVING condition to the query.
        
        Parameters
        ----------
        expression : Union[Having, str]
            The HAVING condition to add. If a string, it will be treated as a HAVING expression.
            
        Returns
        -------
        The added Having object
        """
        if self.having is None:
            self.having = []
            
        if isinstance(expression, Having):
            having = expression
        else:
            having = Having(expression=expression)
            
        having._parent = self
        self.having.append(having)
        return having
    
    def add_aggregation(self, aggregation):
        """
        Add an aggregation expression to the query.
        
        Parameters
        ----------
        aggregation : AggregationExpression
            The aggregation expression to add
            
        Returns
        -------
        The added aggregation
        """
        aggregation._parent = self
        self.aggregations.append(aggregation)
        return aggregation
    
    def add_group_by(self, variables=None):
        """
        Add a GROUP BY clause to the query.
        
        Parameters
        ----------
        variables : Union[str, List[str]], optional
            Variable(s) to group by. If None, creates an empty GroupBy.
            
        Returns
        -------
        The GroupBy object
        """
        if isinstance(variables, str):
            variables = [variables]
        elif variables is None:
            variables = []
            
        if self.group_by is None:
            self.group_by = GroupBy(variables=variables)
            self.group_by._parent = self
        else:
            for var in variables:
                self.group_by.add(var)
                
        return self.group_by
    
    def add_order_by(self, variables=None, ascending=True):
        """
        Add an ORDER BY clause to the query.
        
        Parameters
        ----------
        variables : Union[str, List[str]], optional
            Variable(s) to order by. If None, creates an empty OrderBy.
        ascending : Union[bool, List[bool]], optional
            Whether to sort in ascending order (default is True)
            
        Returns
        -------
        The OrderBy object
        """
        if isinstance(variables, str):
            variables = [variables]
        elif variables is None:
            variables = []
            
        if self.order_by is None:
            self.order_by = OrderBy(variables=variables, ascending=ascending)
            self.order_by._parent = self
        else:
            if isinstance(variables, list):
                for i, var in enumerate(variables):
                    asc = ascending[i] if isinstance(ascending, list) and i < len(ascending) else ascending
                    self.order_by.add(var, asc)
                    
        return self.order_by
    
    def set_limit(self, limit):
        """
        Set the LIMIT value for the query.
        
        Parameters
        ----------
        limit : int
            The limit value
            
        Returns
        -------
        self
            For method chaining
        """
        self.limit = limit
        return self
    
    def set_offset(self, offset):
        """
        Set the OFFSET value for the query.
        
        Parameters
        ----------
        offset : int
            The offset value
            
        Returns
        -------
        self
            For method chaining
        """
        self.offset = offset
        return self
    
    def set_distinct(self, is_distinct=True):
        """
        Set the DISTINCT flag for the query.
        
        Parameters
        ----------
        is_distinct : bool, optional
            Whether the query should use DISTINCT (default is True)
            
        Returns
        -------
        self
            For method chaining
        """
        self.is_distinct = is_distinct
        return self

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
        distinct = "DISTINCT " if self.is_distinct else ""
        
        # Handle projection with aggregations
        if self.aggregations:
            projection_parts = []
            # Add regular variables
            if self.projection_variables != ['*']:
                projection_parts.extend(self.projection_variables)
            
            # Add aggregation expressions
            for agg in self.aggregations:
                distinct_keyword = "DISTINCT " if agg.distinct else ""
                if agg.variable == "*" and agg.function == "COUNT":
                    agg_expr = f"({agg.function}({distinct_keyword}*) AS {agg.alias})"
                else:
                    agg_expr = f"({agg.function}({distinct_keyword}{agg.variable}) AS {agg.alias})"
                projection_parts.append(agg_expr)
            
            projection_str = " ".join(projection_parts)
        else:
            projection_str = " ".join(self.projection_variables)
            
        query = f"SELECT {distinct}{projection_str}\n"
        
        if self.graph:
            query += f"FROM <{self.graph}>\n"
        query += "WHERE {\n"
        query += self._serialize_where_clause(self.where_clause, 1)
        # Only include top-level filters (those not associated with any BGP or GroupGraphPattern)
        if self.filters:
            for filter in self.filters:
                query += f"  FILTER({filter.expression})\n"
        query += "}"
        
        # Add GROUP BY if present
        if self.group_by and self.group_by.variables:
            query += f"\nGROUP BY {' '.join(self.group_by.variables)}"
        
        # Add HAVING if present
        if self.having:
            for having in self.having:
                query += f"\nHAVING({having.expression})"
        
        # Add ORDER BY if present
        if self.order_by:
            query += "\nORDER BY "
            terms = []
            
            # Handle either a single boolean or a list of booleans
            if isinstance(self.order_by.ascending, bool):
                # Same direction for all variables
                direction = "ASC" if self.order_by.ascending else "DESC"
                for var in self.order_by.variables:
                    terms.append(f"{direction}({var})")
            else:
                # Different directions per variable
                for i, var in enumerate(self.order_by.variables):
                    if i < len(self.order_by.ascending):
                        direction = "ASC" if self.order_by.ascending[i] else "DESC"
                        terms.append(f"{direction}({var})")
                    else:
                        # Default to ASC if we run out of direction flags
                        terms.append(f"ASC({var})")
            
            query += " ".join(terms)
        if self.limit is not None:
            query += f"\nLIMIT {self.limit}"
        if self.offset is not None:
            query += f"\nOFFSET {self.offset}"
        return query

    def _serialize_where_clause(
            self,
            clause: Union[BGP, UnionOperator, OptionalOperator, SubQuery, GroupGraphPattern, List[
                Union['BGP', 'UnionOperator', 'OptionalOperator', 'SubQuery', 'GroupGraphPattern']]],
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
        elif isinstance(clause, GroupGraphPattern):
            return self._serialize_group(clause, indent)
        elif isinstance(clause, list):
            return ''.join(self._serialize_where_clause(sq, indent) for sq in clause)
        else:
            raise ValueError(f"Unknown clause type: {type(clause)}")

    def _serialize_bgp(self, bgp: BGP, indent: int) -> str:
        result = ""
        for triple in bgp.triples:
            result += "  " * indent + f"{triple.subject} {triple.predicate} {triple.object} .\n"
        # Add any filters associated with this BGP
        for filter in bgp.filters:
            result += "  " * indent + f"FILTER({filter.expression})\n"
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

    def _serialize_group(self, group: GroupGraphPattern, indent: int) -> str:
        result = "  " * indent + "{\n"
        result += self._serialize_where_clause(group.pattern, indent + 1)
        # Add any filters associated with this group
        for filter in group.filters:
            result += "  " * (indent + 1) + f"FILTER({filter.expression})\n"
        result += "  " * indent + "}\n"
        return result

    def replace_triple_patterns_with_subqueries(self, limit: int = 300) -> 'SPARQLQuery':
        new_query = copy.deepcopy(self)
        new_query.where_clause = self._replace_clause(new_query.where_clause, limit)
        return new_query

    def _replace_clause(
            self,
            clause: Union[BGP, UnionOperator, OptionalOperator, SubQuery, GroupGraphPattern, List[SubQuery]],
            limit: int
    ) -> Union[BGP, UnionOperator, OptionalOperator, SubQuery, GroupGraphPattern, List[SubQuery]]:
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
        elif isinstance(clause, GroupGraphPattern):
            clause.pattern = self._replace_clause(clause.pattern, limit)
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
            clause: Union[BGP, UnionOperator, OptionalOperator, SubQuery, GroupGraphPattern, List[SubQuery]]
    ) -> int:
        if isinstance(clause, BGP):
            return len(clause.triples)
        elif isinstance(clause, UnionOperator):
            return self._count_triple_patterns(clause.left) + self._count_triple_patterns(clause.right)
        elif isinstance(clause, OptionalOperator):
            return self._count_triple_patterns(clause.bgp)
        elif isinstance(clause, SubQuery):
            return clause.query.n_triple_patterns
        elif isinstance(clause, GroupGraphPattern):
            return self._count_triple_patterns(clause.pattern)
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
            clause: Union[BGP, UnionOperator, OptionalOperator, SubQuery, GroupGraphPattern, List[SubQuery]]
    ) -> int:
        if isinstance(clause, BGP):
            return 1
        elif isinstance(clause, UnionOperator):
            return self._count_bgps_recursive(clause.left) + self._count_bgps_recursive(clause.right)
        elif isinstance(clause, OptionalOperator):
            return self._count_bgps_recursive(clause.bgp)
        elif isinstance(clause, SubQuery):
            return clause.query.count_bgps()
        elif isinstance(clause, GroupGraphPattern):
            return self._count_bgps_recursive(clause.pattern)
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
            
        elif isinstance(clause1, GroupGraphPattern):
            return self._compare_clauses(clause1.pattern, clause2.pattern, variable_mapping)

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

    def __str__(self) -> str:
        """
        Return a string representation of the query structure.
        
        Returns
        -------
        str
            The string representation of the query structure.
        """
        result = []
        result.append("SPARQLQuery:")
        
        # Print projection variables
        distinct_str = "DISTINCT " if self.is_distinct else ""
        
        projection_parts = []
        # Add regular variables
        if self.projection_variables != ['*']:
            projection_parts.append(f"{distinct_str}{', '.join(self.projection_variables)}")
        else:
            projection_parts.append(f"{distinct_str}*")
        
        # Add aggregation expressions if present
        if self.aggregations:
            agg_strs = []
            for agg in self.aggregations:
                distinct_keyword = "DISTINCT " if agg.distinct else ""
                if agg.variable == "*" and agg.function == "COUNT":
                    agg_strs.append(f"({agg.function}({distinct_keyword}*) AS {agg.alias})")
                else:
                    agg_strs.append(f"({agg.function}({distinct_keyword}{agg.variable}) AS {agg.alias})")
            projection_parts.append(", ".join(agg_strs))
        
        result.append(f"  Projection: {' '.join(projection_parts)}")
        
        # Print other parts of the query
        if self.graph:
            result.append(f"  Graph: {self.graph}")
        
        if self.filters:
            result.append(f"  Filters:")
            for filter in self.filters:
                result.append(f"    {filter.expression}")
        
        if self.group_by:
            result.append(f"  GroupBy: {', '.join(self.group_by.variables)}")
        
        if self.having:
            result.append(f"  Having:")
            for having in self.having:
                result.append(f"    {having.expression}")
        
        if self.order_by:
            result.append(f"  OrderBy:")
            
            # Handle either a single boolean or a list of booleans
            if isinstance(self.order_by.ascending, bool):
                # Same direction for all variables
                direction = "ASC" if self.order_by.ascending else "DESC"
                result.append(f"    {direction} {', '.join(self.order_by.variables)}")
            else:
                # Different directions per variable
                order_terms = []
                for i, var in enumerate(self.order_by.variables):
                    if i < len(self.order_by.ascending):
                        direction = "ASC" if self.order_by.ascending[i] else "DESC"
                        order_terms.append(f"{direction}({var})")
                    else:
                        # Default to ASC if we run out of direction flags
                        order_terms.append(f"ASC({var})")
                result.append(f"    {', '.join(order_terms)}")
        
        if self.limit is not None:
            result.append(f"  Limit: {self.limit}")
        
        if self.offset is not None:
            result.append(f"  Offset: {self.offset}")
        
        result.append(f"  Where Clause:")
        
        # Use the existing _str_clause logic but capture the output
        clause_lines = self._str_clause(self.where_clause)
        for line in clause_lines:
            result.append(f"  {line}")
        
        return "\n".join(result)
    
    def _str_clause(self, clause, indent=2) -> List[str]:
        """
        Generate string representation of a clause in the query structure.
        
        Parameters
        ----------
        clause : Union[BGP, UnionOperator, OptionalOperator, SubQuery, GroupGraphPattern, List]
            The clause to stringify.
        indent : int, optional
            The indentation level (default is 2).
            
        Returns
        -------
        List[str]
            List of lines representing the clause.
        """
        result = []
        prefix = " " * indent
        
        if isinstance(clause, BGP):
            result.append(f"{prefix}BGP:")
            for triple in clause.triples:
                result.append(f"{prefix}  Triple: {triple.subject} {triple.predicate} {triple.object}")
            # Add filters associated with this BGP
            if clause.filters:
                result.append(f"{prefix}  Filters:")
                for filter in clause.filters:
                    result.append(f"{prefix}    {filter.expression}")
        
        elif isinstance(clause, UnionOperator):
            result.append(f"{prefix}UNION:")
            result.append(f"{prefix}  Left:")
            left_lines = self._str_clause(clause.left, indent + 4)
            result.extend(left_lines)
            result.append(f"{prefix}  Right:")
            right_lines = self._str_clause(clause.right, indent + 4)
            result.extend(right_lines)
        
        elif isinstance(clause, OptionalOperator):
            result.append(f"{prefix}OPTIONAL:")
            optional_lines = self._str_clause(clause.bgp, indent + 2)
            result.extend(optional_lines)
        
        elif isinstance(clause, SubQuery):
            result.append(f"{prefix}SUBQUERY:")
            sub_result = clause.query.__str__().split('\n')
            for line in sub_result[1:]:  # Skip the first line which is 'SPARQLQuery:'
                result.append(f"{prefix}  {line}")
        
        elif isinstance(clause, GroupGraphPattern):
            result.append(f"{prefix}GroupGraphPattern:")
            group_lines = self._str_clause(clause.pattern, indent + 2)
            result.extend(group_lines)
            # Add filters associated with this GroupGraphPattern
            if clause.filters:
                result.append(f"{prefix}  Filters:")
                for filter in clause.filters:
                    result.append(f"{prefix}    {filter.expression}")
        
        elif isinstance(clause, list):
            for i, subquery in enumerate(clause):
                result.append(f"{prefix}GroupGraphPattern:")
                subq_lines = self._str_clause(subquery, indent + 2)
                result.extend(subq_lines)
        
        else:
            result.append(f"{prefix}Unknown clause type: {type(clause)}")
            
        return result
    
    # Keep the old method for backward compatibility
    def print_structure(self, indent=0):
        """
        Print the hierarchical structure of the query.
        
        Parameters
        ----------
        indent : int, optional
            The initial indentation level (default is 0).
        """
        print(self.__str__())


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