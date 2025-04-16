class SPARQLValidationError(Exception):
    """Base class for SPARQL validation errors."""
    pass

class OrderByValidationError(SPARQLValidationError):
    """Raised when there is an error in the ORDER BY clause validation."""
    pass 