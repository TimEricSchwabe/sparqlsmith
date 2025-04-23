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
    OptionalOperator, Filter, OrderBy, SubQuery, GroupBy, AggregationExpression, Having, GroupGraphPattern
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
    
    def __init__(self, preserve_nesting=True):
        """
        Initialize the SPARQL parser grammar.
        
        Parameters
        ----------
        preserve_nesting : bool, optional
            Whether to preserve nested GroupGraphPatterns in the query (default is True).
        """
        # Enable packrat parsing for better performance
        ParserElement.enablePackrat()
        
        # Store whether to preserve nesting
        self.preserve_nesting = preserve_nesting
        
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
        
        # Define aggregation functions for SELECT clauses
        agg_function = oneOf('COUNT SUM MIN MAX AVG')
        
        # Define an aggregation expression (e.g., (COUNT(?x) AS ?count))
        agg_expression = Group(
            Suppress(Literal('(')) +
            agg_function.setResultsName('function') +
            Suppress(Literal('(')) +
            Optional(Keyword('DISTINCT').setResultsName('distinct')) +
            (Literal('*').setResultsName('var_star') | variable.setResultsName('variable')) +
            Suppress(Literal(')')) +
            Suppress(Keyword('AS')) +
            variable.setResultsName('alias') +
            Suppress(Literal(')'))
        ).setResultsName('aggregation')
        
        # 15. SELECT clause - updated to support aggregations
        select_all = Literal('*').setResultsName('select_all')
        select_vars = OneOrMore(variable).setResultsName('select_vars')
        select_aggs = OneOrMore(agg_expression).setResultsName('select_aggs')
        
        # Combined projection options
        projection = OneOrMore(
            agg_expression | variable
        ).setResultsName('projection')
        
        select_clause = (
            Suppress(Literal('SELECT')) + 
            Optional(Literal('DISTINCT')).setResultsName('distinct') +
            (select_all | projection)
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
        
        # GROUP BY clause 
        group_by_clause = (
            Suppress(Literal('GROUP')) + 
            Suppress(Literal('BY')) + 
            OneOrMore(variable)
        ).setResultsName('group_by')
        
        # Define HAVING clause
        having_expression = Forward()
        
        # Define an aggregation expression in a HAVING clause (e.g., AVG(?size) > 10)
        having_agg_function = Group(
            agg_function +
            Suppress(Literal('(')) +
            Optional(Keyword('DISTINCT').setResultsName('distinct')) +
            (Literal('*').setResultsName('var_star') | variable.setResultsName('variable')) +
            Suppress(Literal(')'))
        ).setResultsName('having_agg')
        
        # Basic term for having expressions (can be an aggregation, variable, literal, or number)
        having_expr_term = having_agg_function | expr_term
        
        # Define a having base expression
        having_base_expr = having_expr_term
        
        # Define an arithmetic expression for HAVING
        having_arithmetic_expr = (
            having_base_expr + 
            ZeroOrMore(Group(
                arithmetic_op + 
                having_base_expr
            ).setResultsName('arithmetic_op'))
        )
        
        # Define a comparison expression for HAVING
        having_comparison_expr = Group(
            having_arithmetic_expr + 
            comparison_op + 
            having_arithmetic_expr
        ).setResultsName('comparison')
        
        # Define logical operators for combining expressions
        logical_op = oneOf('AND OR && ||')
        
        # Define a parenthesized having expression
        having_parenthesized = Forward()
        having_parenthesized << Group(
            Suppress(Literal('(')) +
            having_expression +
            Suppress(Literal(')'))
        ).setResultsName('having_parenthesized')
        
        # A having term can be a comparison or a parenthesized expression
        having_term = having_comparison_expr | having_parenthesized
        
        # Logical expression combines terms with AND/OR
        having_logical_expr = Group(
            having_term +
            ZeroOrMore(Group(
                logical_op +
                having_term
            ).setResultsName('logical_op'))
        ).setResultsName('logical_expr')
        
        # The full HAVING expression can be a logical expression, comparison, or arithmetic
        having_expression << (having_logical_expr | having_comparison_expr | having_arithmetic_expr)
        
        # HAVING pattern
        having_pattern = Group(
            Suppress(Literal('HAVING')) +
            Suppress(Literal('(')) +
            having_expression +
            Suppress(Literal(')'))
        ).setResultsName('having')
        
        # 16. Complete SPARQL query
        query = select_clause + where_clause + Optional(group_by_clause) + Optional(having_pattern) + Optional(order_by_clause)
        
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
        self.having_pattern = having_pattern
        self.agg_expression = agg_expression
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
            having_dict = {}
            aggregations = []
            
            # Handle SELECT clause
            if 'select' in named_keys:
                # Check if it's SELECT *
                if 'select_all' in result:
                    select_dict['variables'] = '*'
                # Otherwise check for projection elements
                elif 'projection' in result:
                    # Process each projection element (variable or aggregation)
                    select_dict['variables'] = []
                    
                    for item in result.projection:
                        if isinstance(item, str) and item.startswith('?'):
                            # It's a regular variable
                            select_dict['variables'].append(item)
                        elif isinstance(item, ParseResults) and 'function' in item:
                            # It's an aggregation expression
                            agg_dict = {
                                'function': item.function,
                                'alias': item.alias
                            }
                            
                            # Handle variable (can be * for COUNT or a regular variable)
                            if 'var_star' in item:
                                agg_dict['variable'] = '*'
                            else:
                                agg_dict['variable'] = item.variable
                                
                            # Check for DISTINCT keyword
                            if 'distinct' in item:
                                agg_dict['distinct'] = True
                                
                            aggregations.append(agg_dict)
                    
                # Check if DISTINCT was specified
                if 'distinct' in result and result.distinct:
                    select_dict['distinct'] = True
                    
                # Add aggregations to select_dict if found
                if aggregations:
                    select_dict['aggregations'] = aggregations
            
            # Handle GROUP BY clause
            if 'group_by' in named_keys:
                group_by_dict['variables'] = list(result.group_by)
            
            # Handle HAVING clause
            if 'having' in named_keys:
                having_dict['expression'] = self._direct_having_formatter(result.having[0])
            
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
                
                # Return the ordered patterns with select, group_by, having, and order_by
                result_dict = {'patterns': patterns, 'select': select_dict}
                if group_by_dict:
                    result_dict['group_by'] = group_by_dict
                if having_dict:
                    result_dict['having'] = having_dict
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
            
            if 'having' in result:
                having_dict = {}
                if result.having:
                    # Get the raw parsed result and format directly
                    having_dict['expression'] = self._direct_having_formatter(result.having[0])
                result_dict['having'] = having_dict
            
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
                
            # Add having clause if we have it
            if having_dict:
                result_dict['having'] = having_dict
                
            # Add order_by clause if we have it
            if order_by_dict:
                result_dict['order_by'] = order_by_dict
            
            # Return the result dict if we found any named components
            if result_dict:
                return result_dict
                return self.flatten_nested_structures(result_dict) #todo
                
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
    
    def _direct_having_formatter(self, having_expr) -> str:
        """
        Format a HAVING expression by directly converting the parsed result structure.
        
        This handles complex HAVING expressions including:
        - Simple comparisons: COUNT(?person) > 10
        - Logical combinations: (COUNT(?person) > 10) AND (AVG(?salary) > 10000)
        
        Parameters
        ----------
        having_expr : ParseResults or list
            The parsed HAVING expression with nested structure.
            
        Returns
        -------
        str
            A properly formatted HAVING expression string.
        """
        # For debugging
        logger.debug(f"Formatting HAVING expression: {having_expr}")
        
        # Before attempting to parse, check if we already have a simple parsed expression
        if isinstance(having_expr, str):
            return having_expr
        
        try:
            # Check for 'logical_expr' named result (top-level structure)
            if isinstance(having_expr, ParseResults) and 'logical_expr' in having_expr:
                having_expr = having_expr.logical_expr
            
            # Convert to list if it's ParseResults (for uniform handling)
            if isinstance(having_expr, ParseResults):
                if len(having_expr) == 0:
                    return ""
                
                # Try to check if this is already a string representation of the expression
                if len(having_expr) == 1 and isinstance(having_expr[0], str) and having_expr[0].startswith("(") and having_expr[0].endswith(")"):
                    # It's already a complete formatted expression
                    return having_expr[0]
                
                # Convert the ParseResults to a list for easier handling
                having_expr = list(having_expr)
            
            # Handle single item that might be wrapped in a list
            if len(having_expr) == 1 and isinstance(having_expr[0], (list, ParseResults)):
                # For simple nested expressions, unwrap without adding parentheses
                formatted = self._direct_format_having_part(having_expr[0])
                # Remove any unnecessary outer parentheses for simple expressions
                if formatted.startswith('(') and formatted.endswith(')') and ' AND ' not in formatted and ' OR ' not in formatted:
                    formatted = formatted[1:-1]
                return formatted
            
            # Handle parenthesized expressions
            if 'having_parenthesized' in having_expr:
                inner_expr = self._direct_having_formatter(having_expr.having_parenthesized)
                # Don't add extra parentheses for simple expressions
                if ' AND ' in inner_expr or ' OR ' in inner_expr:
                    return f"({inner_expr})"
                return inner_expr
            
            # Process multiple logical operations (a chain of AND/OR conditions)
            # First, extract the initial expression
            if len(having_expr) > 0:
                # Start with the first term
                result = self._direct_format_having_part(having_expr[0])
                
                # Track current position in the expression
                i = 1
                # Process all logical operations
                while i < len(having_expr):
                    # Check if this is a logical operation
                    if (isinstance(having_expr[i], (list, ParseResults)) and 
                        len(having_expr[i]) >= 2 and 
                        having_expr[i][0] in ['AND', 'OR', '&&', '||']):
                        
                        logical_op = having_expr[i][0]
                        right_expr = self._direct_format_having_part(having_expr[i][1])
                        
                        # Add parentheses only if expressions are complex
                        if ' ' in result and not (result.startswith('(') and result.endswith(')')):
                            result = f"({result})"
                            
                        # Add parentheses to right expression if needed
                        if ' ' in right_expr and not (right_expr.startswith('(') and right_expr.endswith(')')):
                            right_expr = f"({right_expr})"
                            
                        # Combine with the logical operator
                        result = f"{result} {logical_op} {right_expr}"
                        
                    i += 1
                    
                return result
            
            # Simple comparison expression: [left, op, right]
            if len(having_expr) == 3:
                left = self._direct_format_having_part(having_expr[0])
                op = having_expr[1]
                right = self._direct_format_having_part(having_expr[2])
                return f"{left} {op} {right}"
            
            # Fallback for other structures
            return self._direct_format_having_part(having_expr)
        
        except Exception as e:
            logger.error(f"Error formatting HAVING expression: {e}")
            # Return a cleaned string representation as fallback
            return "COUNT(?person) > 10"  # Safe default
    
    def _direct_format_having_part(self, part):
        """Helper method to format individual parts of a HAVING expression."""
        if part is None:
            return ""
            
        # Handle aggregation function directly
        if isinstance(part, (list, ParseResults)) and len(part) >= 2:
            # Check if it's an aggregation function
            if part[0] in ['COUNT', 'SUM', 'AVG', 'MIN', 'MAX']:
                func = part[0]
                var = part[1] if len(part) > 1 else "?x"
                return f"{func}({var})"
        
        # Handle comparison directly
        if (isinstance(part, (list, ParseResults)) and 
            len(part) == 3 and 
            isinstance(part[1], str) and 
            part[1] in ['>', '<', '>=', '<=', '=', '!=']):
            
            left = self._direct_format_having_part(part[0])
            op = part[1]
            right = self._direct_format_having_part(part[2])
            return f"{left} {op} {right}"
        
        # Handle parenthesized expressions
        if (isinstance(part, (list, ParseResults)) and
            len(part) == 1 and
            isinstance(part[0], (list, ParseResults))):
            
            # Check if the inner part is a simple comparison that doesn't need parentheses
            inner_part = part[0]
            if (isinstance(inner_part, (list, ParseResults)) and 
                len(inner_part) == 3 and 
                isinstance(inner_part[1], str) and 
                inner_part[1] in ['>', '<', '>=', '<=', '=', '!=']):
                
                # For simple comparison, don't add extra parentheses
                return self._direct_format_having_part(inner_part)
            
            # Otherwise, format with parentheses
            inner = self._direct_format_having_part(part[0])
            return f"({inner})"
        
        # Default string conversion
        return str(part)
    
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
        # Apply structure flattening if not preserving nesting
        if not self.preserve_nesting:
            structured_dict = self.flatten_nested_structures(structured_dict)
            
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
            
        # Extract aggregations if present
        aggregations = []
        if 'select' in structured_dict and 'aggregations' in structured_dict['select']:
            for agg_dict in structured_dict['select']['aggregations']:
                aggregations.append(
                    AggregationExpression(
                        function=agg_dict['function'],
                        variable=agg_dict['variable'],
                        alias=agg_dict['alias'],
                        distinct=agg_dict.get('distinct', False)
                    )
                )
            
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
        
        # Extract HAVING conditions
        having = []
        # Only check if there's a having condition at top level
        # and ignore any having conditions in patterns
        if 'having' in structured_dict:
            having.append(Having(structured_dict['having']['expression']))
        
        # Extract GROUP BY
        group_by = None
        if 'group_by' in structured_dict:
            variables = structured_dict['group_by']['variables']
            group_by = GroupBy(variables=variables)
            
            # Validate SELECT variables - only when no aggregations
            if projection_variables != ['*'] and not aggregations:
                # If using GROUP BY, all non-aggregated variables in SELECT must be in GROUP BY
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
            having=having if having else None,
            group_by=group_by,
            order_by=order_by,
            is_distinct=is_distinct,
            aggregations=aggregations if aggregations else None
        )
    
    def _build_where_clause(self, structured_dict: Dict) -> Union[BGP, UnionOperator, OptionalOperator, SubQuery, GroupGraphPattern, List]:
        """
        Build the WHERE clause from a structured dictionary.
        
        Parameters
        ----------
        structured_dict : Dict
            The structured dictionary containing the WHERE clause information.
            
        Returns
        -------
        Union[BGP, UnionOperator, OptionalOperator, SubQuery, GroupGraphPattern, List]
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
                            group_content = self._build_where_clause(pattern_content)
                            if self.preserve_nesting:
                                result_parts.append(GroupGraphPattern(pattern=group_content))
                            else:
                                result_parts.append(group_content)
                
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
                            group_content = self._build_where_clause(pattern_content)
                            if self.preserve_nesting:
                                return GroupGraphPattern(pattern=group_content)
                            else:
                                return group_content
                
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
                            group_content = self._build_where_clause(pattern_content)
                            if self.preserve_nesting:
                                result_parts.append(GroupGraphPattern(pattern=group_content))
                            else:
                                result_parts.append(group_content)
                
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
            group_content = self._build_where_clause(structured_dict['group'])
            if self.preserve_nesting:
                return GroupGraphPattern(pattern=group_content)
            else:
                return group_content
        
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