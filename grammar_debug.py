#!/usr/bin/env python3

from pyparsing import (
    Word, Literal, Group, OneOrMore, QuotedString, Suppress, Forward,
    alphas, alphanums, Combine, CharsNotIn, pyparsing_common as ppc, 
    ParserElement, ParseResults, Optional, ZeroOrMore, oneOf, Keyword, ParseException
)
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def traverse_parse_results(result, indent=0):
    """
    Recursively traverse and print the structure of parsed results.
    
    Parameters
    ----------
    result : ParseResults or list or dict
        The parsed results to traverse
    indent : int
        Current indentation level for pretty printing
    """
    prefix = "  " * indent
    
    if isinstance(result, ParseResults):
        # Print the named results first
        if hasattr(result, 'keys'):
            for key in result.keys():
                print(f"{prefix}Named Result '{key}':")
                traverse_parse_results(result[key], indent + 1)
        
        # Then print the list items
        if len(result) > 0:
            print(f"{prefix}List items:")
            for i, item in enumerate(result):
                print(f"{prefix}  Item {i}:")
                traverse_parse_results(item, indent + 2)
    
    elif isinstance(result, (list, tuple)):
        print(f"{prefix}List:")
        for i, item in enumerate(result):
            print(f"{prefix}  Item {i}:")
            traverse_parse_results(item, indent + 2)
    
    elif isinstance(result, dict):
        print(f"{prefix}Dict:")
        for key, value in result.items():
            print(f"{prefix}  Key '{key}':")
            traverse_parse_results(value, indent + 2)
    
    else:
        print(f"{prefix}Value: {result}")

def convert_to_structured_dict(result):
    """
    Convert pyparsing ParseResults to a clean, structured dictionary.
    
    Parameters
    ----------
    result : ParseResults
        The parsed results to convert
        
    Returns
    -------
    dict
        A structured dictionary representation
    """
    # For debugging
    if isinstance(result, ParseResults) and hasattr(result, 'keys'):
        logger.debug(f"Result keys: {list(result.keys())}")
    
    if isinstance(result, ParseResults):
        # Check if we have multiple patterns that should be preserved in order
        named_keys = list(result.keys()) if hasattr(result, 'keys') else []
        
        # If we have braced/optional/union/filter etc., preserve their order
        if len(named_keys) > 1:
            # Create a patterns list to preserve order
            patterns = []
            
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
                    braced_result = convert_to_structured_dict(result.braced)
                    patterns.append({'group': braced_result})
                
                elif key == 'optional':
                    optional_dict = {}
                    if 'braced' in result.optional:
                        optional_dict['pattern'] = convert_to_structured_dict(result.optional.braced)
                    patterns.append({'optional': optional_dict})
                
                elif key == 'union':
                    union_dict = {}
                    if 'left' in result.union:
                        union_dict['left'] = convert_to_structured_dict(result.union.left)
                    if 'right' in result.union:
                        union_dict['right'] = convert_to_structured_dict(result.union.right)
                    patterns.append({'union': union_dict})
                
                elif key == 'filter':
                    filter_dict = {}
                    if result.filter:
                        filter_dict['expression'] = str(result.filter[0])
                    patterns.append({'filter': filter_dict})
            
            # Return the ordered patterns
            return {'patterns': patterns}
        
        
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
                union_dict['left'] = convert_to_structured_dict(result.union.left)
            if 'right' in result.union:
                union_dict['right'] = convert_to_structured_dict(result.union.right)
            result_dict['union'] = union_dict
        
        if 'optional' in result:
            optional_dict = {}
            if 'braced' in result.optional:
                optional_dict['pattern'] = convert_to_structured_dict(result.optional.braced)
            result_dict['optional'] = optional_dict
        
        if 'filter' in result:
            filter_dict = {}
            if result.filter:
                filter_dict['expression'] = str(result.filter[0])
            result_dict['filter'] = filter_dict
        
        if 'braced' in result:
            # Process the braced pattern
            braced_result = convert_to_structured_dict(result.braced)
            
            # Check if we can flatten nested groups
            if isinstance(braced_result, dict) and len(braced_result) == 1 and 'group' in braced_result:
                # This is a group that contains only another group - flatten it
                result_dict['group'] = braced_result['group']
            else:
                # Regular group processing
                result_dict['group'] = braced_result
        
        # Return the result dict if we found any named components
        if result_dict:
            return flatten_nested_structures(result_dict)
            
        # If we didn't find any named components but there are list items,
        # check if it looks like a triple pattern
        if len(result) > 0:
            if len(result) == 3 and all(isinstance(item, str) or isinstance(item, (int, float)) for item in result):
                return list(result)
            
            # Otherwise process as a list
            return [convert_to_structured_dict(item) for item in result]
    
    # If it's a list/tuple
    elif isinstance(result, (list, tuple)):
        return [convert_to_structured_dict(item) for item in result]
    
    # Return scalars as-is
    else:
        return result

def flatten_nested_structures(result_dict):
    """
    Recursively flatten unnecessary nesting in the result dictionary.
    
    Parameters
    ----------
    result_dict : dict
        The structured dictionary to flatten
        
    Returns
    -------
    dict
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
            return flatten_nested_structures(group_content)
    
    # For all other cases, process each value recursively
    flattened_dict = {}
    for key, value in result_dict.items():
        if isinstance(value, dict):
            flattened_dict[key] = flatten_nested_structures(value)
        elif isinstance(value, list):
            flattened_dict[key] = [
                flatten_nested_structures(item) if isinstance(item, dict) else item 
                for item in value
            ]
        else:
            flattened_dict[key] = value
    
    return flattened_dict

def parse_and_show_results(parser, test_str, description):
    print(f"\n=== Testing: {description} ===")
    print(f"Input: {test_str}")
    try:
        result = parser.parseString(test_str, parseAll=True)
        print(f"Success! Raw Result: {result.asList()}")
        
        # Convert to structured dictionary
        structured_dict = convert_to_structured_dict(result)
        print(f"Structured Dict: {structured_dict}")
        
    except ParseException as e:
        print(f"Failed! Error: {e}")

# Define and test basic elements one by one

# 1. Variable (e.g., ?x, ?name)
variable = Combine(Literal('?') + Word(alphas, alphanums + '_'))
#parse_and_show_results(variable, "?abc", "variable")
#parse_and_show_results(variable, "?x123", "variable with numbers")

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
#parse_and_show_results(iri, "<http://example.org/resource>", "IRI")
#parse_and_show_results(iri, "ns:resource", "prefixed name IRI")
#parse_and_show_results(iri, ":resource", "prefixed name IRI")


# 3. Literal values (strings, numbers, booleans)
string_literal = QuotedString('"') | QuotedString("'")
numeric_literal = ppc.number

#parse_and_show_results(string_literal, '"hello"', "string literal with double quotes")
#parse_and_show_results(string_literal, "'world'", "string literal with single quotes")
#parse_and_show_results(numeric_literal, "42", "numeric literal integer")
#parse_and_show_results(numeric_literal, "3.14", "numeric literal float")
#parse_and_show_results(boolean_literal, "true", "boolean literal true")
#parse_and_show_results(boolean_literal, "false", "boolean literal false")
#parse_and_show_results(iri, "true", "IRI with 'true' - should fail")
#parse_and_show_results(iri, "ex:true", "IRI with ex:true - should succeed")


# 4. Term (variable, IRI, or literal)
term_s_p = variable | iri
term_o = variable | iri | string_literal | numeric_literal | boolean_literal
#parse_and_show_results(term_s_p, "?x", "term as variable")
#parse_and_show_results(term_s_p, "<http://example.org/resource>", "term as IRI")
#parse_and_show_results(term_s_p, "ns:resource", "term as prefixed name IRI")
#parse_and_show_results(term_s_p, ":resource", "term as prefixed name IRI")
#parse_and_show_results(term_s_p, "true", "term_s_p with boolean - should fail")
#parse_and_show_results(term_o, '"value"', "term as string")
#parse_and_show_results(term_s_p, "123", "term as number")
#parse_and_show_results(term_o, "true", "term_o with boolean - should succeed")


# Triple pattern (subject predicate object .)
triple_pattern = Group(
    term_s_p + term_s_p + term_o + Suppress(Literal('.'))
).setResultsName('triple_pattern')

# Basic Graph Pattern (one or more triple patterns)
bgp = Group(
    OneOrMore(triple_pattern)
).setResultsName('bgp')

#parse_and_show_results(triple_pattern, "?s ?p ?o .", "simple triple pattern")
#parse_and_show_results(triple_pattern, "?s <http://example.org/predicate> 42 .", "mixed triple pattern")
#parse_and_show_results(triple_pattern, "?s :predicate :test .", "mixed triple pattern")




# 6. Basic Graph Pattern (BGP)
#parse_and_show_results(bgp, "?s ?p ?o .", "BGP with one triple")
#parse_and_show_results(bgp, "?s :p :o . ?x ?y ?z .", "BGP with multiple triples")



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

# Test expressions with the new grammar
#parse_and_show_results(expr_term, "?x", "simple term (variable)")
#parse_and_show_results(expr_term, "5", "simple term (numeric)")
#parse_and_show_results(parenthesized, "(?x)", "parenthesized variable")
#parse_and_show_results(arithmetic_expr, "?x + 10", "simple arithmetic")
#parse_and_show_results(arithmetic_expr, "?x + ?y + 5", "complex arithmetic")
#parse_and_show_results(comparison_expr, "?x > 5", "comparison expression")
#parse_and_show_results(expression, "(?x + 2) > (?y - 1)", "complex expression")
#parse_and_show_results(expression, "?x > ?y + 5", "comparison with arithmetic")

# Update filter_pattern to use the new expression
filter_pattern = Group(
    Suppress(Literal('FILTER')) +
    Suppress(Literal('(')) +
    expression +
    Suppress(Literal(')'))
).setResultsName('filter')

#parse_and_show_results(filter_pattern, "FILTER(?x > 5)", "filter with comparison")
#parse_and_show_results(filter_pattern, "FILTER(((?x + (?y - 3)) > (5 * ?z)))", "filter with arithmetic in comparison")



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

# Test the braced pattern parser
#parse_and_show_results(group_graph_pattern, "{{{{ ?s ?p ?o . }}}}", "braced pattern")

# Test braced pattern with extra content (should fail with parseAll=True)
#parse_and_show_results(braced_pattern, "{ ?s ?p ?o . } ?s ?p ?o .", "braced pattern with extra content (should fail with parseAll=True)")

# Test nested pattern with triple block afterward (should pass for group_graph_pattern)
#parse_and_show_results(group_graph_pattern, "{?s ?p ?o.} ?s ?p ?o.", "nested pattern followed by triple block")




# Test UNION pattern
union_test = "{ ?s ?p ?o . } UNION {?o ?p ?s . }"
#parse_and_show_results(union_pattern, union_test, "UNION pattern")



# Test nested UNION pattern
nested_union_test = "{ ?s ?p ?o . } UNION { { ?x ?y ?z . } UNION { ?a ?b ?c . } }"
#parse_and_show_results(union_pattern, nested_union_test, "nested UNION pattern")



# Test OPTIONAL pattern
#optional_test = "?s ?p ?o. OPTIONAL { ?o ?p ?s . }"
#parse_and_show_results(group_graph_pattern, optional_test, "OPTIONAL pattern")

#optional_test = "{?s ?p ?o.} OPTIONAL { ?o ?p ?s . }"
#parse_and_show_results(group_graph_pattern, optional_test, "OPTIONAL pattern")





# Test combined patterns
#combined_pattern = "?s ?p ?o . { ?x ?y ?z . } UNION { ?a ?b ?c . } OPTIONAL { ?d ?e ?f . }"
#parse_and_show_results(group_graph_pattern, combined_pattern, "combined pattern with BGP, UNION, OPTIONAL")



# Test FILTER in graph pattern
filter_test = "?s ?p ?o . FILTER(?o > 5)"
#parse_and_show_results(group_graph_pattern, filter_test, "graph pattern with FILTER")



# 14. WHERE clause
where_clause = (
    Suppress(Literal('WHERE')) + 
    Suppress(Literal('{')) + 
    group_graph_pattern + 
    Suppress(Literal('}'))
).setResultsName('where')

#parse_and_show_results(where_clause, "WHERE { ?s ?p ?o . FILTER(?o > 5) }", "simple WHERE clause")



#parse_and_show_results(
#    where_clause, 
#    "WHERE { { ?s ?p ?o . } UNION { ?o ?p ?s . } }", 
#    "WHERE clause with UNION"
#)

#parse_and_show_results(
#    where_clause, 
#    "WHERE { ?s ?p ?o . { ?x ?y ?z . } UNION { ?a ?b ?c . } OPTIONAL { ?d ?e ?f . }}", 
#    "WHERE clause with UNION"
#)



# 15. SELECT clause
select_all = Literal('*').setResultsName('select_all')
select_vars = OneOrMore(variable).setResultsName('select_vars')

select_clause = (
    Suppress(Literal('SELECT')) + 
    Optional(Literal('DISTINCT')) +
    (select_all | select_vars)
).setResultsName('select')

parse_and_show_results(select_clause, "SELECT *", "SELECT * clause")
parse_and_show_results(select_clause, "SELECT ?s ?p ?o", "SELECT with variables")
parse_and_show_results(select_clause, "SELECT DISTINCT ?s", "SELECT DISTINCT")


exit()


# 16. Complete SPARQL query
query = select_clause + where_clause

# Test complete queries
parse_and_show_results(
    query, 
    "SELECT ?s ?p ?o WHERE { ?s ?p ?o . }", 
    "basic complete query"
)
parse_and_show_results(
    query, 
    "SELECT ?s ?p ?o WHERE { ?s ?p ?o . FILTER(?o > 5) }", 
    "query with filter"
)
parse_and_show_results(
    query, 
    "SELECT ?s ?p ?o WHERE { { ?s ?p ?o . } UNION { ?o ?p ?s . } }", 
    "query with UNION"
)
parse_and_show_results(
    query, 
    "SELECT ?s ?p ?o WHERE { ?s ?p ?o . OPTIONAL { ?o ?p ?x . } }", 
    "query with OPTIONAL"
)
parse_and_show_results(
    query, 
    "SELECT ?s ?p ?o WHERE { { { ?s ?p ?o . } } }", 
    "query with nested braces"
) 