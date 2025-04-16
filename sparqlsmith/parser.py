#!/usr/bin/env python3

from pyparsing import (
    Word, Literal, Group, OneOrMore, QuotedString, Suppress, Forward,
    alphas, alphanums, Combine, CharsNotIn, pyparsing_common as ppc, 
    ParserElement, ParseResults, Optional, ZeroOrMore, oneOf, Keyword, ParseException
)
import logging
from typing import Dict, List, Union, Any
from .query import (
    SPARQLQuery, BGP, TriplePattern, UnionOperator, 
    OptionalOperator, Filter, OrderBy, SubQuery, GroupBy
)
from .errors import OrderByValidationError

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


class SPARQLParser:
    """
    A parser for SPARQL queries that uses pyparsing to implement the grammar.
    
    This parser converts SPARQL query strings into structured dictionaries
    and then into SPARQLQuery objects.
    """
    
    def __init__(self):
        """Initialize the SPARQL parser grammar."""
        # Enable packrat parsing for better performance
        ParserElement.enablePackrat()
        
        # Define the grammar
        self._define_grammar()
    
    def _define_grammar(self):
        """Define the SPARQL grammar using pyparsing."""
        # 1. Variable (e.g., ?x, ?name)
        variable = Combine(Literal('?') + Word(alphas, alphanums + '_'))
        
        # 2. IRI (e.g., <http://example.org/resource>)
        # IRI can be either a full IRI in angle brackets or a prefixed name
        full_iri = Combine(Literal('<') + CharsNotIn('>') + Literal('>'))
        
        # Define boolean literals as keywords
        boolean_literal = Keyword('true') | Keyword('false')
        
        # Define prefixed name to match namespace:value pattern
        prefixed_name = (
            Combine(Word(alphas) + Literal(':') + Word(alphanums + '_')) | 
            Combine(Literal(':') + Word(alphanums + '_'))
        )
        
        iri = full_iri | prefixed_name
        
        # 3. Literal values (strings, numbers, booleans)
        string_literal = QuotedString('"') | QuotedString("'")
        numeric_literal = ppc.number
        
        # 4. Term (variable, IRI, or literal)
        term_s_p = variable | iri
        term_o = variable | iri | string_literal | numeric_literal | boolean_literal
        
        # Triple pattern (subject predicate object .)
        triple_pattern = Group(
            term_s_p + term_s_p + term_o + Suppress(Literal('.'))
        ).setResultsName('triple_pattern')
        
        # Basic Graph Pattern (one or more triple patterns)
        bgp = Group(
            OneOrMore(triple_pattern)
        ).setResultsName('bgp')
        
        # 7. Expression for FILTER
        expression = Forward()
        comparison_op = oneOf('= != < > <= >=')
        arithmetic_op = oneOf('+ - * /')
        
        # Basic term for expressions (can be a variable, literal, or number)
        expr_term = term_o
        
        # Define parenthesized expressions first to prevent recursion issues
        parenthesized = Forward()
        parenthesized << Group(
            Suppress(Literal('(')) + 
            expression + 
            Suppress(Literal(')'))
        ).setResultsName('parenthesized')
        
        # Define a base expression (term or parenthesized)
        base_expr = parenthesized | expr_term
        
        # Define an arithmetic expression
        arithmetic_expr = Forward()
        arithmetic_expr << (
            base_expr + 
            ZeroOrMore(Group(
                arithmetic_op + 
                base_expr
            ).setResultsName('arithmetic_op'))
        )
        
        # Define a comparison expression
        comparison_expr = Group(
            arithmetic_expr + 
            comparison_op + 
            arithmetic_expr
        ).setResultsName('comparison')
        
        # The full expression can be comparison or arithmetic
        expression << (comparison_expr | arithmetic_expr)
        
        # Update filter_pattern to use the new expression
        filter_pattern = Group(
            Suppress(Literal('FILTER')) +
            Suppress(Literal('(')) +
            expression +
            Suppress(Literal(')'))
        ).setResultsName('filter')
        
        # 9. Define a group_graph_pattern (recursive)
        group_graph_pattern = Forward()
        
        # 10. Braced pattern
        braced_pattern = Group(
            Suppress(Literal('{')) +
            group_graph_pattern +
            Suppress(Literal('}'))
        ).setResultsName('braced')
        
        # 11. Optional pattern
        optional_pattern = Group(
            Suppress(Literal('OPTIONAL')) +
            braced_pattern
        ).setResultsName('optional')
        
        # 12. Union pattern
        union_pattern = Group(
            braced_pattern.setResultsName('left') +
            Suppress(Literal('UNION')) +
            braced_pattern.setResultsName('right')
        ).setResultsName('union')
        
        # 13. Complete group_graph_pattern
        graph_pattern_not_triples = (
            union_pattern |
            optional_pattern |
            braced_pattern |
            filter_pattern
        )
        
        # Update the definition to handle patterns like {GraphPatternNotTriples TriplesBlock}
        group_graph_pattern << (
            Optional(bgp) +
            ZeroOrMore(graph_pattern_not_triples + Optional(bgp))
        )
        
        # 14. WHERE clause
        where_clause = (
            Suppress(Literal('WHERE')) + 
            Suppress(Literal('{')) + 
            group_graph_pattern + 
            Suppress(Literal('}'))
        ).setResultsName('where')
        
        # 15. SELECT clause
        select_all = Literal('*').setResultsName('select_all')
        select_vars = OneOrMore(variable).setResultsName('select_vars')
        
        select_clause = (
            Suppress(Literal('SELECT')) + 
            Optional(Literal('DISTINCT')).setResultsName('distinct') +
            (select_all | select_vars)
        ).setResultsName('select')
        
        # Define a variable that could be in parentheses
        var_in_parens = Group(
            Suppress(Literal('(')) + 
            variable +
            Suppress(Literal(')'))
        ).setResultsName('var_in_parens')
        
        # Define a plain variable term for ORDER BY
        plain_var_term = variable.copy().setResultsName('var')
        
        # Define a directional term (ASC/DESC)
        direction_term = (
            (Literal('ASC') | Literal('DESC')).setResultsName('direction') +
            var_in_parens
        )
        
        # An order by term can be either a plain variable or a direction term
        order_by_term = (direction_term | plain_var_term)
        
        # ORDER BY clause accepts one or more order by terms
        order_by_clause = (
            Suppress(Literal('ORDER')) + 
            Suppress(Literal('BY')) + 
            OneOrMore(order_by_term)
        ).setResultsName('order_by')
        
        # GROUP BY clause (supports only variables for now)
        group_by_clause = (
            Suppress(Literal('GROUP')) + 
            Suppress(Literal('BY')) + 
            OneOrMore(variable)
        ).setResultsName('group_by')
        
        # 16. Complete SPARQL query
        query = select_clause + where_clause + Optional(group_by_clause) + Optional(order_by_clause)
        
        # Save grammar elements as instance variables
        self.variable = variable
        self.iri = iri
        self.term_s_p = term_s_p
        self.term_o = term_o
        self.triple_pattern = triple_pattern
        self.bgp = bgp
        self.filter_pattern = filter_pattern
        self.braced_pattern = braced_pattern
        self.optional_pattern = optional_pattern
        self.union_pattern = union_pattern
        self.where_clause = where_clause
        self.select_clause = select_clause
        self.order_by_clause = order_by_clause
        self.group_by_clause = group_by_clause
        self.query = query
    
    def parse(self, query_string: str) -> Dict:
        """
        Parse a SPARQL query string into a structured dictionary.
        
        Parameters
        ----------
        query_string : str
            The SPARQL query string to parse.
            
        Returns
        -------
        Dict
            A structured dictionary representation of the parsed query.
        """
        try:
            parse_result = self.query.parseString(query_string, parseAll=True)
            return self.convert_to_structured_dict(parse_result)
        except ParseException as e:
            logger.error(f"Parse error: {e}")
            raise
    
    def convert_to_structured_dict(self, result: ParseResults) -> Dict:
        """
        Convert pyparsing ParseResults to a clean, structured dictionary.
        
        Parameters
        ----------
        result : ParseResults
            The parsed results to convert
            
        Returns
        -------
        Dict
            A structured dictionary representation
        """
        # For debugging
        if isinstance(result, ParseResults) and hasattr(result, 'keys'):
            logger.debug(f"Result keys: {list(result.keys())}")
        
        if isinstance(result, ParseResults):
            # Check if we have multiple patterns that should be preserved in order
            named_keys = list(result.keys()) if hasattr(result, 'keys') else []

            select_dict = {}
            patterns = []
            order_by_dict = {}
            group_by_dict = {}
            
            # Handle SELECT clause
            if 'select' in named_keys:
                # Check if it's SELECT *
                if 'select_all' in result:
                    select_dict['variables'] = '*'
                # Otherwise it's a list of variables
                elif 'select_vars' in result:
                    select_dict['variables'] = list(result.select_vars)
                
                # Check if DISTINCT was specified
                if 'distinct' in result and result.distinct:
                    select_dict['distinct'] = True
            
            # Handle GROUP BY clause
            if 'group_by' in named_keys:
                group_by_dict['variables'] = list(result.group_by)
            
            # Handle ORDER BY clause
            if 'order_by' in named_keys:
                order_by_vars = []
                ascending_flags = []
                
                # Handle multiple order by terms
                i = 0
                while i < len(result.order_by):
                    term = result.order_by[i]
                    
                    # Case 1: Plain variable (e.g., ?age)
                    if isinstance(term, str) and term.startswith('?'):
                        order_by_vars.append(term)
                        ascending_flags.append(True)  # Default is ascending
                        i += 1
                    
                    # Case 2: Direction + variable in parentheses (e.g., DESC(?age))
                    elif term in ['ASC', 'DESC'] and i+1 < len(result.order_by):
                        direction = term
                        # Get the variable from the nested ParseResults
                        var_list = result.order_by[i+1]
                        if len(var_list) > 0:
                            var = var_list[0]
                            order_by_vars.append(var)
                            ascending_flags.append(direction != 'DESC')
                        i += 2  # Skip the direction and variable group
                    else:
                        # Skip unrecognized terms
                        i += 1
                
                order_by_dict['variables'] = order_by_vars
                order_by_dict['ascending'] = ascending_flags
            
            # If we have braced/optional/union/filter etc., preserve their order
            if len(named_keys) > 1:
                # Create a patterns list to preserve order
                
                # Loop through named_keys in order to preserve original pattern sequence
                for key in named_keys:
                    if key == 'bgp':
                        bgp_dict = {'bgp': {'triple_patterns': []}}
                        for item in result.bgp:
                            if 'triple_pattern' in item:
                                bgp_dict['bgp']['triple_patterns'].append(list(item.triple_pattern))
                            else:
                                bgp_dict['bgp']['triple_patterns'].append(list(item))
                        patterns.append(bgp_dict)
                    
                    elif key == 'braced':
                        braced_result = self.convert_to_structured_dict(result.braced)
                        patterns.append({'group': braced_result})
                    
                    elif key == 'optional':
                        optional_dict = {}
                        if 'braced' in result.optional:
                            optional_dict['pattern'] = self.convert_to_structured_dict(result.optional.braced)
                        patterns.append({'optional': optional_dict})
                    
                    elif key == 'union':
                        union_dict = {}
                        if 'left' in result.union:
                            union_dict['left'] = self.convert_to_structured_dict(result.union.left)
                        if 'right' in result.union:
                            union_dict['right'] = self.convert_to_structured_dict(result.union.right)
                        patterns.append({'union': union_dict})
                    
                    elif key == 'filter':
                        filter_dict = {}
                        if result.filter:
                            # Format the filter expression for better readability
                            filter_dict['expression'] = self._format_filter_expression(result.filter[0])
                        patterns.append({'filter': filter_dict})
                
                # Return the ordered patterns with select, group_by, and order_by
                result_dict = {'patterns': patterns, 'select': select_dict}
                if group_by_dict:
                    result_dict['group_by'] = group_by_dict
                if order_by_dict:
                    result_dict['order_by'] = order_by_dict
                return result_dict
            
            # Single component case - process as before
            result_dict = {}
            
            if 'bgp' in result:
                patterns = []
                for item in result.bgp:
                    if 'triple_pattern' in item:
                        patterns.append(list(item.triple_pattern))
                    else:
                        patterns.append(list(item))
                result_dict['bgp'] = {'triple_patterns': patterns}
            
            if 'union' in result:
                union_dict = {}
                if 'left' in result.union:
                    union_dict['left'] = self.convert_to_structured_dict(result.union.left)
                if 'right' in result.union:
                    union_dict['right'] = self.convert_to_structured_dict(result.union.right)
                result_dict['union'] = union_dict
            
            if 'optional' in result:
                optional_dict = {}
                if 'braced' in result.optional:
                    optional_dict['pattern'] = self.convert_to_structured_dict(result.optional.braced)
                result_dict['optional'] = optional_dict
            
            if 'filter' in result:
                filter_dict = {}
                if result.filter:
                    # Format the filter expression for better readability
                    filter_dict['expression'] = self._format_filter_expression(result.filter[0])
                result_dict['filter'] = filter_dict
            
            if 'braced' in result:
                # Process the braced pattern
                braced_result = self.convert_to_structured_dict(result.braced)
                
                # Check if we can flatten nested groups
                if isinstance(braced_result, dict) and len(braced_result) == 1 and 'group' in braced_result:
                    # This is a group that contains only another group - flatten it
                    result_dict['group'] = braced_result['group']
                else:
                    # Regular group processing
                    result_dict['group'] = braced_result
            
            # Add select clause if we have it
            if select_dict:
                result_dict['select'] = select_dict
            
            # Add group_by clause if we have it
            if group_by_dict:
                result_dict['group_by'] = group_by_dict
                
            # Add order_by clause if we have it
            if order_by_dict:
                result_dict['order_by'] = order_by_dict
            
            # Return the result dict if we found any named components
            if result_dict:
                return self.flatten_nested_structures(result_dict)
                
            # If we didn't find any named components but there are list items,
            # check if it looks like a triple pattern
            if len(result) > 0:
                if len(result) == 3 and all(isinstance(item, str) or isinstance(item, (int, float)) for item in result):
                    return list(result)
                
                # Otherwise process as a list
                return [self.convert_to_structured_dict(item) for item in result]
        
        # If it's a list/tuple
        elif isinstance(result, (list, tuple)):
            return [self.convert_to_structured_dict(item) for item in result]
        
        # Return scalars as-is
        else:
            return result
    
    def _format_filter_expression(self, expr) -> str:
        """
        Format a filter expression for better readability.
        
        Parameters
        ----------
        expr : ParseResults
            The parsed filter expression.
            
        Returns
        -------
        str
            A formatted string representation of the filter expression.
        """
        if isinstance(expr, ParseResults):
            # For comparison expressions
            if 'comparison' in expr:
                comp = expr.comparison
                if len(comp) >= 3:
                    left = self._format_filter_expression(comp[0])
                    op = comp[1]
                    right = self._format_filter_expression(comp[2])
                    return f"{left} {op} {right}"
            
            # For arithmetic expressions
            if len(expr) > 0:
                # If there are arithmetic operations
                if 'arithmetic_op' in expr:
                    left = self._format_filter_expression(expr[0])
                    ops = []
                    for i in range(len(expr.arithmetic_op)):
                        op = expr.arithmetic_op[i][0]
                        right = self._format_filter_expression(expr.arithmetic_op[i][1])
                        ops.append(f"{op} {right}")
                    return f"{left} {' '.join(ops)}"
                # If it's a parenthesized expression
                elif 'parenthesized' in expr:
                    return f"({self._format_filter_expression(expr.parenthesized)})"
                # If it's just a term
                else:
                    # If it has multiple items (like a list)
                    if len(expr) > 1:
                        return ' '.join(str(item) for item in expr)
                    # If it's a single item
                    return str(expr[0])
        
        # Default case: return as string
        return str(expr)
    
    def flatten_nested_structures(self, result_dict: Dict) -> Dict:
        """
        Recursively flatten unnecessary nesting in the result dictionary.
        
        Parameters
        ----------
        result_dict : Dict
            The structured dictionary to flatten
            
        Returns
        -------
        Dict
            The flattened dictionary
        """
        # Base case: if it's not a dictionary, return as is
        if not isinstance(result_dict, dict):
            return result_dict
        
        # Check for group-only nesting
        if len(result_dict) == 1 and 'group' in result_dict:
            group_content = result_dict['group']
            if isinstance(group_content, dict) and len(group_content) == 1 and 'group' in group_content:
                # Recursive case: we have nested groups, flatten them
                return self.flatten_nested_structures(group_content)
        
        # For all other cases, process each value recursively
        flattened_dict = {}
        for key, value in result_dict.items():
            if isinstance(value, dict):
                flattened_dict[key] = self.flatten_nested_structures(value)
            elif isinstance(value, list):
                flattened_dict[key] = [
                    self.flatten_nested_structures(item) if isinstance(item, dict) else item 
                    for item in value
                ]
            else:
                flattened_dict[key] = value
        
        return flattened_dict
    
    def structured_dict_to_query(self, structured_dict: Dict) -> SPARQLQuery:
        """
        Convert a structured dictionary to a SPARQLQuery object.
        
        Parameters
        ----------
        structured_dict : Dict
            The structured dictionary representation of a SPARQL query.
            
        Returns
        -------
        SPARQLQuery
            A SPARQLQuery object representing the query.
        """
        # Extract SELECT variables
        projection_variables = ['*']  # Default
        if 'select' in structured_dict and 'variables' in structured_dict['select']:
            if structured_dict['select']['variables'] == '*':
                projection_variables = ['*']
            else:
                projection_variables = structured_dict['select']['variables']
        
        # Extract distinct flag
        is_distinct = False
        if 'select' in structured_dict and 'distinct' in structured_dict['select']:
            is_distinct = structured_dict['select']['distinct']
            
        # For debugging
        logger.debug(f"Converting structured dict: {structured_dict}")
        
        # Extract filters
        filters = []
        # Check if this is a filter at top level
        if 'filter' in structured_dict:
            filters.append(Filter(structured_dict['filter']['expression']))
        
        # Check if there are filters in patterns
        if 'patterns' in structured_dict:
            for pattern in structured_dict['patterns']:
                if 'filter' in pattern:
                    filters.append(Filter(pattern['filter']['expression']))
        
        # Extract GROUP BY
        group_by = None
        if 'group_by' in structured_dict:
            variables = structured_dict['group_by']['variables']
            group_by = GroupBy(variables=variables)
            
            # Validate SELECT variables
            if projection_variables != ['*']:
                # If using GROUP BY, all non-aggregated variables in SELECT must be in GROUP BY
                # For now, we just assume there are no aggregates
                for var in projection_variables:
                    if var not in variables:
                        raise OrderByValidationError(f"Non-group key variable in SELECT: {var}")
        
        # Extract ORDER BY
        order_by = None
        if 'order_by' in structured_dict:
            variables = structured_dict['order_by']['variables']
            
            # Check if we have a list of ascending flags or a single value
            if 'ascending' in structured_dict['order_by']:
                ascending = structured_dict['order_by']['ascending']
                
                # If we have a single ascending flag but multiple variables
                if isinstance(ascending, bool) and len(variables) > 1:
                    # Apply the same direction to all variables
                    ascending = [ascending] * len(variables)
                    
                order_by = OrderBy(variables=variables, ascending=ascending)
        
        # Build the where clause
        where_clause = self._build_where_clause(structured_dict)
        
        # Create and return the SPARQLQuery
        return SPARQLQuery(
            projection_variables=projection_variables,
            where_clause=where_clause,
            filters=filters if filters else None,
            group_by=group_by,
            order_by=order_by,
            is_distinct=is_distinct
        )
    
    def _build_where_clause(self, structured_dict: Dict) -> Union[BGP, UnionOperator, OptionalOperator, SubQuery, List]:
        """
        Build the WHERE clause from a structured dictionary.
        
        Parameters
        ----------
        structured_dict : Dict
            The structured dictionary containing the WHERE clause information.
            
        Returns
        -------
        Union[BGP, UnionOperator, OptionalOperator, SubQuery, List]
            The corresponding WHERE clause object.
        """
        logger.debug(f"Building where clause from: {structured_dict}")
        
        # Handle patterns list (multiple patterns in order)
        if 'patterns' in structured_dict:
            # Process all BGPs first to combine them
            all_triples = []
            other_patterns = []
            
            for pattern in structured_dict['patterns']:
                if 'bgp' in pattern:
                    for triple_pattern in pattern['bgp']['triple_patterns']:
                        all_triples.append(TriplePattern(
                            subject=triple_pattern[0],
                            predicate=triple_pattern[1],
                            object=triple_pattern[2]
                        ))
                else:
                    # Save non-BGP patterns separately
                    other_patterns.append(pattern)
            
            # If we have BGP triples and other patterns, combine them in the right order
            if all_triples:
                # First we have a BGP
                result_parts = [BGP(all_triples)]
                
                # Then process other patterns in order
                for pattern in other_patterns:
                    for pattern_type, pattern_content in pattern.items():
                        if pattern_type == 'union':
                            result_parts.append(UnionOperator(
                                left=self._build_where_clause(pattern_content['left']),
                                right=self._build_where_clause(pattern_content['right'])
                            ))
                        elif pattern_type == 'optional':
                            result_parts.append(OptionalOperator(
                                bgp=self._build_where_clause(pattern_content['pattern'])
                            ))
                        elif pattern_type == 'group':
                            result_parts.append(self._build_where_clause(pattern_content))
                
                # If we have only one part, return it directly
                if len(result_parts) == 1:
                    return result_parts[0]
                # Otherwise, return the list
                return result_parts
            
            # If we have only other patterns, process them separately
            if other_patterns:
                # Special case: if only one pattern, return it directly
                if len(other_patterns) == 1:
                    for pattern_type, pattern_content in other_patterns[0].items():
                        if pattern_type == 'union':
                            return UnionOperator(
                                left=self._build_where_clause(pattern_content['left']),
                                right=self._build_where_clause(pattern_content['right'])
                            )
                        elif pattern_type == 'optional':
                            return OptionalOperator(
                                bgp=self._build_where_clause(pattern_content['pattern'])
                            )
                        elif pattern_type == 'group':
                            return self._build_where_clause(pattern_content)
                
                # Multiple patterns, build them in order
                result_parts = []
                for pattern in other_patterns:
                    for pattern_type, pattern_content in pattern.items():
                        if pattern_type == 'union':
                            result_parts.append(UnionOperator(
                                left=self._build_where_clause(pattern_content['left']),
                                right=self._build_where_clause(pattern_content['right'])
                            ))
                        elif pattern_type == 'optional':
                            result_parts.append(OptionalOperator(
                                bgp=self._build_where_clause(pattern_content['pattern'])
                            ))
                        elif pattern_type == 'group':
                            result_parts.append(self._build_where_clause(pattern_content))
                
                # Return as list
                return result_parts
        
        # Handle BGP
        if 'bgp' in structured_dict:
            triples = []
            for triple_pattern in structured_dict['bgp']['triple_patterns']:
                triples.append(TriplePattern(
                    subject=triple_pattern[0],
                    predicate=triple_pattern[1],
                    object=triple_pattern[2]
                ))
            return BGP(triples)
        
        # Handle UNION
        elif 'union' in structured_dict:
            return UnionOperator(
                left=self._build_where_clause(structured_dict['union']['left']),
                right=self._build_where_clause(structured_dict['union']['right'])
            )
        
        # Handle OPTIONAL
        elif 'optional' in structured_dict:
            return OptionalOperator(
                bgp=self._build_where_clause(structured_dict['optional']['pattern'])
            )
        
        # Handle Group
        elif 'group' in structured_dict:
            return self._build_where_clause(structured_dict['group'])
        
        # Default empty BGP
        return BGP()
    
    def parse_to_query(self, query_string: str) -> SPARQLQuery:
        """
        Parse a SPARQL query string directly into a SPARQLQuery object.
        
        Parameters
        ----------
        query_string : str
            The SPARQL query string to parse.
            
        Returns
        -------
        SPARQLQuery
            A SPARQLQuery object representing the query.
        """
        structured_dict = self.parse(query_string)
        return self.structured_dict_to_query(structured_dict)

def debug_parse_results(result, level=0):
    """Print the structure of parse results for debugging."""
    indent = "  " * level
    if isinstance(result, ParseResults):
        print(f"{indent}ParseResults({len(result)})")
        if hasattr(result, 'keys'):
            for key in result.keys():
                print(f"{indent}  Key: {key}")
                debug_parse_results(result[key], level + 2)
        for i, item in enumerate(result):
            print(f"{indent}  Item {i}:")
            debug_parse_results(item, level + 2)
    else:
        print(f"{indent}Value: {result}") 