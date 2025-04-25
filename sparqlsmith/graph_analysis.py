import networkx as nx
from typing import List

def determine_graph_shape(triples):
    """
    Determine the shape of a graph formed by triple patterns.
    
    Parameters
    ----------
    triples : List
        List of triple patterns, each with subject, predicate, and object attributes
        
    Returns
    -------
    str
        The shape name as a string: Single-triple, Path, Star, Snowflake, Tree, Cycle, Flower, or Complex
    """
    if not triples:
        return "Empty"
    
    if len(triples) == 1:
        return "Single-triple"
    
    # Create a directed graph from the triples
    G = nx.DiGraph()
    
    # Add edges for each triple (subject -> object via predicate)
    for triple in triples:
        G.add_edge(triple.subject, triple.object, predicate=triple.predicate)
    
    # Create an undirected version for certain analyses
    G_undirected = G.to_undirected()
    
    # Check if it's a cycle
    if len(G) == len(triples) and all(G.out_degree(n) == 1 and G.in_degree(n) == 1 for n in G.nodes):
        return "Cycle"
    
    # Check if it's a path (linear chain)
    if all(G.out_degree(n) <= 1 and G.in_degree(n) <= 1 for n in G.nodes):
        # A path should have exactly 2 endpoints
        endpoints = [n for n in G.nodes if G.out_degree(n) + G.in_degree(n) == 1]
        if len(endpoints) == 2:
            return "Path"
    
    # Check if it's a star
    degrees = [G_undirected.degree(n) for n in G_undirected.nodes]
    if (len([d for d in degrees if d > 1]) == 1 and 
        all(d == 1 or d > 2 for d in degrees)):
        return "Star"
    
    # Check if it's a tree (connected and acyclic)
    if nx.is_tree(G_undirected):
        # Find hub nodes (degree > 2)
        hub_nodes = [n for n in G_undirected.nodes if G_undirected.degree(n) > 2]
        
        # If there are no hub nodes, it's a simple path
        if len(hub_nodes) == 0:
            return "Path"
        
        # Check if it's a flower pattern - strict definition
        # A flower has exactly one hub node with one long stem path (length >= 2)
        if len(hub_nodes) == 1:
            hub_node = hub_nodes[0]
            # Get neighbors of the hub
            neighbors = list(G_undirected.neighbors(hub_node))
            
            # We need one path of length >= 2 going out from the hub
            stems_found = 0

            # Create a new graph without the hub to analyze each potential stem
            H = G_undirected.copy()
            H.remove_node(hub_node)
            for neighbor in neighbors:
                # For each neighbor, find the connected component it belongs to
                component = nx.node_connected_component(H, neighbor)
                # A stem is a path with length > 1
                if len(component) > 1:
                    # Check if this component forms a path
                    subgraph = H.subgraph(component)
                    # A path has all nodes with degree <= 2 and exactly 2 nodes with degree 1
                    if (all(subgraph.degree(n) <= 2 for n in subgraph.nodes) and
                        len([n for n in subgraph.nodes if subgraph.degree(n) == 1]) == 2):
                        stems_found += 1
            
            # A flower must have exactly one stem
            if stems_found == 1:
                return "Flower"
        
        # Default tree case
        return "Tree"
    
    # If it has cycles but is not a simple cycle, it's complex
    return "Complex" 