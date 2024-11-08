#!/usr/bin/env python3

import os
import shutil
from rdflib import Graph, URIRef
from rdflib.term import Literal
from rdflib.namespace import XSD
import json
from typing import Any

def parse_args():
    import argparse
    parser = argparse.ArgumentParser(description="Split an RO-Crate into atomic elements by EntryPoints.")
    parser.add_argument("input_path", type=str, help="Path to the input RO-Crate directory.")
    parser.add_argument("--output_prefix", type=str, default="split", help="Prefix for the output folders.")
    parser.add_argument("--entrypoints", type=str, required=False, help="IDs of entrypoints to consider. Defaults to all found entrypoints. Comma separated.")
    parser.add_argument("--ignore_connections", type=str, required=False, help="List of node connections to ignore in RDF graph for splitting. Comma separated.")
    args = parser.parse_args()
    if args.entrypoints:
        args.entrypoints = args.entrypoints.split(",")
    if args.ignore_connections:
        args.ignore_connections = args.ignore_connections.split(",")
    return args


def jsonld2graph(data: dict[Any: Any], base: str) -> Graph:
    g = Graph()
    g.parse(
        data=data,
        format="json-ld",
        base=base
    )

    return g


def extract_subgraph_for_entrypoint(g: Graph, entrypoint: URIRef, predicates_to_ignore: list[str] = []) -> Graph:
    """ Filter the graph for all nodes connected to the given entrypoint uri.
    Triplets where the predicate is in predicates_to_ignore are ignored """

    subgraph = Graph()

    to_explore = {entrypoint}
    explored = {}

    while len(to_explore) > 0:
        node = to_explore.pop()
        if node in explored:
            continue

        for subj, pred, obj in g.triples((node, None, None)):
            # ignore connecting predicates
            if str(pred) in predicates_to_ignore:
                continue
            subgraph.add((subj, pred, obj))
            # Add linked entities to be explored
            if isinstance(obj, URIRef):
                to_explore.add(obj)

    return subgraph

def find_entrypoints(g: Graph) -> list[URIRef]:
    q = """
        PREFIX schema: <http://schema.org/>

        SELECT ?entity
        WHERE {
            ?entity a schema:EntryPoint .
            FILTER NOT EXISTS {
                ?metadata schema:mainEntity ?entity .
            }
        }
    """
    entrypoints = [r[0] for r in g.query(q)]
    return entrypoints

def extract_rocrate_for_entrypoint(entrypoint: URIRef, destination_path: str, g: Graph, connections_to_ignore: list[str]|None = None) -> Graph:
    """ Extracts the RO-Crate for the given entrypoint and writes it to the destination_path folder.
    Returns the extracted graph"""
    if not connections_to_ignore:
        connections_to_ignore = [
            "http://schema.org/workExample",
            "http://schema.org/isPartOf",
        ]
    sg = extract_subgraph_for_entrypoint(g, entrypoint, predicates_to_ignore=connections_to_ignore)

    # include ro-crate-metadata.json from base crate
    # but filter out triplets pointing to filtered out subjects
    subjects_in_subgraph = set([s for s, _, _ in sg])
    subjects_not_in_subgraph = set([s for s, _, _ in g if s not in subjects_in_subgraph])
    for (s, p, o) in g:
        if str(s).endswith("ro-crate-metadata.json") and o not in subjects_not_in_subgraph:
            sg.add((s, p, o))
        if (str(o).endswith("ro-crate-metadata.json") and s not in subjects_not_in_subgraph):
            sg.add((s, p, o))

    # copy files to new location
    os.makedirs(destination_path, exist_ok=True)
    q = """
        PREFIX schema: <http://schema.org/>
        
        SELECT ?file
        WHERE {
            ?file a schema:MediaObject .
        }
    """
    sg_files = [str(r[0]) for r in sg.query(q)]
    for file in sg_files:
        abs_path = file.replace("file://", "")
        rel_path = os.path.relpath(abs_path, base_path)
        new_location = os.path.join(destination_path, rel_path)
        os.makedirs(os.path.dirname(new_location), exist_ok=True)
        shutil.copy2(abs_path, new_location)
 
    # remove rdf_base from subgraph
    for (s, p, o) in sg:
        sg.remove((s,p,o))
        new_s = URIRef(str(s).replace(rdf_base, ""))
        new_o = URIRef(str(o).replace(rdf_base, ""))
        sg.add((new_s, p, new_o))
    
    # set entrypoint dataset to ./ and fix objects pointing to it
    old_entrypoint = str(entrypoint).replace(rdf_base, "")
    new_entrypoint = "./"
    for (s, p, o) in sg:
        if str(s) == old_entrypoint:
            new_s = URIRef(str(s).replace(old_entrypoint, new_entrypoint))
        else:
            new_s = s
        if str(o) == old_entrypoint:
            new_o = URIRef(str(o).replace(old_entrypoint, new_entrypoint))
        else:
            new_o = o
        sg.remove((s, p, o))
        sg.add((new_s, p, new_o))

    # write metadata
    sg_jsonld = json.loads(sg.serialize(format="json-ld", indent=4, context=metadata["@context"]))
    with open(os.path.join(destination_path, "ro-crate-metadata.json"), "w") as metadata_file:
        metadata_file.write(json.dumps(sg_jsonld, indent=4))

    return sg
 

if __name__ == "__main__":
    args = parse_args()
    base_path = args.input_path
    if base_path.endswith("/"):
        base_path = path_path[:-1]
    
    # load metadata file and create RDF graph
    metadata = json.load(open(os.path.join(base_path, "ro-crate-metadata.json"), "r"))
    rdf_base = f"file://{os.path.abspath(base_path)}/"
    g = jsonld2graph(
        metadata,
        base = rdf_base
    )

    # find Entrypoints in graph
    entrypoints = find_entrypoints(g)
    if args.entrypoints:
        filter = [f"{rdf_base}{filter_ep}" for filter_ep in args.entrypoints]
        entrypoints = [ep for ep in entrypoints if str(ep) in filter]
    print("Found entrypoints: ", [str(e) for e in entrypoints])

    # Extract RO-Crates for entrypoints
    for counter, entrypoint in enumerate(entrypoints):
        print("Creating RO-Crate for ", entrypoint)

        destination_path = os.path.join(args.output_prefix, f"sub-crate{counter+1}")
        print(args.ignore_connections)
        subgraph = extract_rocrate_for_entrypoint(entrypoint, destination_path, g)

        num_files = len(list(subgraph.triples((None, None, URIRef("http://schema.org/MediaObject")))))
        num_entities = len(set([s for s, _, _ in subgraph.triples((None, None, None))]))
        print(f"Created RO-Crate at {destination_path} with {num_files} files and {num_entities} entities")
