from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum, auto
from typing import List, Optional, Union, Any


class FilterNode(ABC):
    """Base abstract class for all nodes in the filter expression AST."""
    
    @abstractmethod
    def to_sparql(self) -> str:
        """Convert this node to its SPARQL string representation."""
        pass


class NodeType(Enum):
    """Enum for different types of filter expression nodes."""
    BINARY_EXPRESSION = auto()
    UNARY_EXPRESSION = auto()
    FUNCTION_CALL = auto()
    VARIABLE = auto()
    LITERAL = auto()


class ValueType(Enum):
    """Enum for different types of literal values."""
    STRING = auto()
    NUMBER = auto()
    BOOLEAN = auto()
    URI = auto()
    DATE = auto()


class BinaryOperator(Enum):
    """Enum for binary operators used in expressions."""
    AND = "&&"
    OR = "||"
    EQUALS = "="
    NOT_EQUALS = "!="
    LESS_THAN = "<"
    LESS_THAN_EQUALS = "<="
    GREATER_THAN = ">"
    GREATER_THAN_EQUALS = ">="
    PLUS = "+"
    MINUS = "-"
    MULTIPLY = "*"
    DIVIDE = "/"
    IN = "IN"  # Special operator for the IN function


class UnaryOperator(Enum):
    """Enum for unary operators used in expressions."""
    NOT = "!"
    NEGATIVE = "-"
    POSITIVE = "+"


@dataclass
class Variable(FilterNode):
    """Represents a variable in a filter expression."""
    name: str  # Variable name including the '?' prefix
    
    def to_sparql(self) -> str:
        return self.name


@dataclass
class Literal(FilterNode):
    """Represents a literal value in a filter expression."""
    value: Any
    value_type: ValueType
    datatype: Optional[str] = None
    language_tag: Optional[str] = None
    
    def to_sparql(self) -> str:
        if self.value_type == ValueType.STRING:
            result = f'"{self.value}"'
            if self.language_tag:
                result += f'@{self.language_tag}'
            elif self.datatype:
                result += f'^^<{self.datatype}>'
            return result
        elif self.value_type == ValueType.BOOLEAN:
            return str(self.value).lower()
        elif self.value_type == ValueType.NUMBER:
            return str(self.value)
        elif self.value_type == ValueType.URI:
            return f'<{self.value}>'
        elif self.value_type == ValueType.DATE:
            # ISO format with datatype
            return f'"{self.value}"^^<http://www.w3.org/2001/XMLSchema#dateTime>'
        return str(self.value)


@dataclass
class BinaryExpression(FilterNode):
    """Represents a binary expression (with two operands)."""
    left: FilterNode
    operator: BinaryOperator
    right: FilterNode
    
    def to_sparql(self) -> str:
        if self.operator == BinaryOperator.IN:
            # Special handling for IN operator
            values = []
            if isinstance(self.right, FunctionCall) and self.right.function_name == "List":
                values = self.right.arguments
            else:
                values = [self.right]
            
            values_str = ", ".join(value.to_sparql() for value in values)
            return f"{self.left.to_sparql()} IN ({values_str})"
        else:
            return f"({self.left.to_sparql()} {self.operator.value} {self.right.to_sparql()})"


@dataclass
class UnaryExpression(FilterNode):
    """Represents a unary expression (with one operand)."""
    operator: UnaryOperator
    operand: FilterNode
    
    def to_sparql(self) -> str:
        return f"{self.operator.value}({self.operand.to_sparql()})"


@dataclass
class FunctionCall(FilterNode):
    """Represents a function call in a filter expression."""
    function_name: str
    arguments: List[FilterNode]
    
    def to_sparql(self) -> str:
        args_str = ", ".join(arg.to_sparql() for arg in self.arguments)
        
        # Special handling for certain functions
        if self.function_name == "EXISTS" or self.function_name == "NOT EXISTS":
            # Assuming the first argument contains the pattern string
            return f"{self.function_name} {{ {args_str} }}"
        else:
            return f"{self.function_name}({args_str})"


# Convenience factory functions to create filter nodes

def and_(*args: FilterNode) -> FilterNode:
    """Create an AND expression from multiple FilterNodes."""
    if len(args) == 0:
        raise ValueError("At least one argument is required for AND operation")
    if len(args) == 1:
        return args[0]
    return BinaryExpression(args[0], BinaryOperator.AND, and_(*args[1:]))


def or_(*args: FilterNode) -> FilterNode:
    """Create an OR expression from multiple FilterNodes."""
    if len(args) == 0:
        raise ValueError("At least one argument is required for OR operation")
    if len(args) == 1:
        return args[0]
    return BinaryExpression(args[0], BinaryOperator.OR, or_(*args[1:]))


def not_(operand: FilterNode) -> FilterNode:
    """Create a NOT expression."""
    return UnaryExpression(UnaryOperator.NOT, operand)


def equals(left: FilterNode, right: FilterNode) -> FilterNode:
    """Create an equality expression."""
    return BinaryExpression(left, BinaryOperator.EQUALS, right)


def not_equals(left: FilterNode, right: FilterNode) -> FilterNode:
    """Create an inequality expression."""
    return BinaryExpression(left, BinaryOperator.NOT_EQUALS, right)


def less_than(left: FilterNode, right: FilterNode) -> FilterNode:
    """Create a less than expression."""
    return BinaryExpression(left, BinaryOperator.LESS_THAN, right)


def greater_than(left: FilterNode, right: FilterNode) -> FilterNode:
    """Create a greater than expression."""
    return BinaryExpression(left, BinaryOperator.GREATER_THAN, right)


def less_than_equals(left: FilterNode, right: FilterNode) -> FilterNode:
    """Create a less than or equal expression."""
    return BinaryExpression(left, BinaryOperator.LESS_THAN_EQUALS, right)


def greater_than_equals(left: FilterNode, right: FilterNode) -> FilterNode:
    """Create a greater than or equal expression."""
    return BinaryExpression(left, BinaryOperator.GREATER_THAN_EQUALS, right)


def regex(text: FilterNode, pattern: FilterNode, flags: Optional[FilterNode] = None) -> FilterNode:
    """Create a REGEX function call."""
    args = [text, pattern]
    if flags:
        args.append(flags)
    return FunctionCall("REGEX", args)


def str_func(arg: FilterNode) -> FilterNode:
    """Create a STR function call."""
    return FunctionCall("STR", [arg])


def exists(pattern: str) -> FilterNode:
    """Create an EXISTS function call."""
    # The pattern is passed as a string directly
    return FunctionCall("EXISTS", [Literal(pattern, ValueType.STRING)])


def not_exists(pattern: str) -> FilterNode:
    """Create a NOT EXISTS function call."""
    # The pattern is passed as a string directly
    return FunctionCall("NOT EXISTS", [Literal(pattern, ValueType.STRING)])


def in_list(var: FilterNode, *values: FilterNode) -> FilterNode:
    """Create an IN expression."""
    # We use a special List function to represent the value list
    value_list = FunctionCall("List", list(values))
    return BinaryExpression(var, BinaryOperator.IN, value_list)


# Simple parser for filter expressions
# Note: This is a very basic implementation and doesn't cover all SPARQL filter syntax
# A more complete parser would use a proper parsing library like pyparsing

import re

class FilterParser:
    """A simple parser for SPARQL filter expressions."""
    
    def __init__(self):
        # Regular expressions for tokenizing
        self.variable_pattern = re.compile(r'\?[a-zA-Z0-9_]+')
        self.string_literal_pattern = re.compile(r'"([^"\\]|\\.)*"')
        self.number_pattern = re.compile(r'\d+(\.\d*)?')
        self.operator_pattern = re.compile(r'(&&|\|\||!=|<=|>=|<|>|=|\+|-|\*|/)')
        self.function_pattern = re.compile(r'[a-zA-Z_][a-zA-Z0-9_]*\s*\(')
        
    def parse(self, filter_string: str) -> FilterNode:
        """
        Parse a SPARQL filter string into a FilterNode AST.
        
        Parameters
        ----------
        filter_string : str
            The SPARQL filter string to parse.
            
        Returns
        -------
        FilterNode
            The root node of the AST.
            
        Notes
        -----
        This is a very simple parser and does not cover all SPARQL filter syntax.
        It's meant as a starting point for a more complete implementation.
        """
        # Handle some common patterns
        
        # Simple variable comparison
        var_comparison = re.match(r'(\?[a-zA-Z0-9_]+)\s*([<>=!]+)\s*(.+)', filter_string)
        if var_comparison:
            var_name, operator, value = var_comparison.groups()
            var_node = Variable(var_name)
            
            # Try to parse the value
            value = value.strip()
            if value.startswith('"') and value.endswith('"'):
                # String literal
                value_node = Literal(value[1:-1], ValueType.STRING)
            elif value.startswith('?'):
                # Another variable
                value_node = Variable(value)
            elif re.match(r'^\d+(\.\d*)?$', value):
                # Numeric literal
                value_node = Literal(float(value) if '.' in value else int(value), ValueType.NUMBER)
            elif value.lower() in ('true', 'false'):
                # Boolean literal
                value_node = Literal(value.lower() == 'true', ValueType.BOOLEAN)
            else:
                # Assume it's a string literal without quotes
                value_node = Literal(value, ValueType.STRING)
            
            # Create the appropriate binary expression
            if operator == '=':
                return equals(var_node, value_node)
            elif operator == '!=':
                return not_equals(var_node, value_node)
            elif operator == '<':
                return less_than(var_node, value_node)
            elif operator == '>':
                return greater_than(var_node, value_node)
            elif operator == '<=':
                return less_than_equals(var_node, value_node)
            elif operator == '>=':
                return greater_than_equals(var_node, value_node)
        
        # Handle REGEX function
        regex_match = re.match(r'REGEX\s*\(\s*STR\s*\(\s*(\?[a-zA-Z0-9_]+)\s*\)\s*,\s*"([^"]*)"\s*(?:,\s*"([^"]*)"\s*)?\)', filter_string, re.IGNORECASE)
        if regex_match:
            var_name, pattern, flags = regex_match.groups()
            var_node = Variable(var_name)
            str_func_node = str_func(var_node)
            pattern_node = Literal(pattern, ValueType.STRING)
            
            if flags:
                flags_node = Literal(flags, ValueType.STRING)
                return regex(str_func_node, pattern_node, flags_node)
            else:
                return regex(str_func_node, pattern_node)
        
        # Handle logical AND/OR
        if '&&' in filter_string:
            parts = filter_string.split('&&')
            return and_(*[self.parse(part.strip()) for part in parts])
        
        if '||' in filter_string:
            parts = filter_string.split('||')
            return or_(*[self.parse(part.strip()) for part in parts])
        
        # Handle NOT expressions
        if filter_string.strip().startswith('!'):
            return not_(self.parse(filter_string.strip()[1:].strip()))
        
        # For more complex cases, return a basic representation
        # This would be extended in a complete implementation
        raise ValueError(f"Could not parse filter expression: {filter_string}")


def parse_filter(filter_string: str) -> FilterNode:
    """
    Parse a SPARQL filter string into a FilterNode AST.
    
    Parameters
    ----------
    filter_string : str
        The SPARQL filter string to parse.
        
    Returns
    -------
    FilterNode
        The root node of the AST.
    """
    parser = FilterParser()
    return parser.parse(filter_string) 