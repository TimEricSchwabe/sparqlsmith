.. sparqlsmith documentation master file, created by
   sphinx-quickstart on Mon May  5 14:29:16 2025.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

sparqlsmith Documentation
===================================

**sparqlsmith** is a Python library for crafting, manipulating and analyzing SPARQL queries. 

**Key features:**

- **Object-Oriented Design**: Each component of a SPARQL query (triple patterns, filters, BGPs, etc.) is represented as a Python object that can be manipulated programmatically.

- **Modular Construction**: Build complex queries incrementally by adding or removing components, without needing to manipulate raw query strings.

- **Automated Query Generation**: Perfect for workflows that require dynamic query generation, avoiding error-prone string concatenation or templating.

- **Structural Analysis**:  Queries can be analyzed for various properties such as the number of triple patterns, variable usage, graph structure and if they are isomorphic to others.

This approach makes sparqlsmith helpful in scenarios where queries need to be programmatically generated, modified, or analyzed as part of larger automated workflows.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   installation
   usage
   modules/index

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
