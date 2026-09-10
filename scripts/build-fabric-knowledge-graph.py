#!/usr/bin/env python3
"""Build detailed Fabric catalog and relationship graph artifacts from metadata."""

import json
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "artifacts" / "fabric-catalog.json"
GRAPH_PATH = ROOT / "artifacts" / "fabric-knowledge-graph.json"
DOT_PATH = ROOT / "artifacts" / "fabric-knowledge-graph.dot"
GUIDE_PATH = ROOT / "artifacts" / "fabric-data-catalog.md"

DOMAIN_RULES = (
    ("Sales & OTC", ("sale", "sales", "otc", "billing", "order", "service_level")),
    ("Customer & Segmentation", ("customer", "rfm", "outlet", "route", "channel")),
    ("Product & Brand", ("material", "brand", "pack", "flavour", "beverage", "product")),
    ("Credit & Collection", ("credit", "overdue")),
    ("Cooler & Equipment", ("cooler", "equipment")),
    ("Visit & Execution", ("visit",)),
    ("Target & Distribution", ("target", "distribution")),
    ("Reference & Operations", ("date", "address", "org", "suborg", "salesoffice", "plant", "warehouse", "fleet", "log", "permission", "user")),
)
SENSITIVE_TERMS = ("credit", "overdue", "amount", "revenue", "customer", "phone", "email", "address", "bank")
GENERIC_KEYS = {"createdon", "createdat", "updatedon", "updatedat", "status", "year", "month", "date", "name", "description"}


def object_id(obj: dict) -> str:
    return f"{obj['schema']}.{obj['name']}"


def domain_for(obj: dict) -> str:
    text = object_id(obj).lower()
    scores = [(domain, sum(term in text for term in terms)) for domain, terms in DOMAIN_RULES]
    domain, score = max(scores, key=lambda item: item[1])
    return domain if score else "Reference & Operations"


def normalized_key(name: str) -> str:
    return name.lower().replace("_", "")


def key_columns(obj: dict) -> list[dict]:
    return [column for column in obj["columns"] if normalized_key(column["COLUMN_NAME"]).endswith("key")]


def sensitivity_for(obj: dict) -> str:
    text = " ".join(column["COLUMN_NAME"].lower() for column in obj["columns"])
    matched = [term for term in SENSITIVE_TERMS if term in text]
    if any(term in matched for term in ("credit", "overdue", "bank", "phone", "email", "address")):
        return "restricted"
    if any(term in matched for term in ("amount", "revenue", "customer")):
        return "internal"
    return "internal"


def build_graph(objects: list[dict]) -> tuple[list[dict], list[dict]]:
    nodes = []
    index: dict[str, list[str]] = defaultdict(list)
    object_lookup = {object_id(obj): obj for obj in objects}
    for obj in objects:
        obj_id = object_id(obj)
        nodes.append({
            "id": obj_id,
            "schema": obj["schema"],
            "name": obj["name"],
            "type": obj["type"],
            "domain": domain_for(obj),
            "sensitivity": sensitivity_for(obj),
            "column_count": len(obj["columns"]),
            "key_columns": [column["COLUMN_NAME"] for column in key_columns(obj)],
        })
        for column in key_columns(obj):
            index[normalized_key(column["COLUMN_NAME"])].append(obj_id)

    pairs: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for key, object_ids in sorted(index.items()):
        if key in GENERIC_KEYS or len(object_ids) < 2 or len(object_ids) > 35:
            continue
        for left_index, source in enumerate(sorted(object_ids)):
            for target in sorted(object_ids)[left_index + 1:]:
                source_column = next(c["COLUMN_NAME"] for c in object_lookup[source]["columns"] if normalized_key(c["COLUMN_NAME"]) == key)
                target_column = next(c["COLUMN_NAME"] for c in object_lookup[target]["columns"] if normalized_key(c["COLUMN_NAME"]) == key)
                pairs[(source, target)].append({
                    "source_column": source_column,
                    "target_column": target_column,
                    "confidence": "high" if source_column == target_column else "candidate",
                })

    edges = []
    for (source, target), matches in sorted(pairs.items()):
        # Keep analytical objects in the visual graph; full catalog retains legacy bk_* views.
        if source.split(".", 1)[1].startswith("bk_") or target.split(".", 1)[1].startswith("bk_"):
            continue
        edges.append({
            "source": source,
            "target": target,
            "relationship": "shared_key",
            "confidence": "high" if all(match["confidence"] == "high" for match in matches) else "candidate",
            "key_matches": matches,
            "evidence": "INFORMATION_SCHEMA.COLUMNS normalized *Key name matches; cardinality and referential constraints not inspected.",
        })
    return nodes, edges


def column_text(column: dict) -> str:
    length = column.get("CHARACTER_MAXIMUM_LENGTH")
    suffix = f"({length})" if length else ""
    nullable = "nullable" if column["IS_NULLABLE"] == "YES" else "not null"
    return f"`{column['COLUMN_NAME']}` {column['DATA_TYPE']}{suffix}, {nullable}"


def write_guide(database: str, objects: list[dict], nodes: list[dict], edges: list[dict]) -> None:
    node_by_id = {node["id"]: node for node in nodes}
    domain_objects: dict[str, list[dict]] = defaultdict(list)
    for obj in objects:
        domain_objects[domain_for(obj)].append(obj)

    lines = [
        "# Fabric Lakehouse Knowledge Graph and Data Catalog",
        "",
        "## Scope and Evidence",
        "",
        f"- Database: `{database}`",
        "- Source: live `INFORMATION_SCHEMA.TABLES` and `INFORMATION_SCHEMA.COLUMNS` export.",
        f"- Inventory: {len(objects)} objects, {sum(len(obj['columns']) for obj in objects)} columns, {len(edges)} shared-key relationship candidates.",
        "- This document inventories accessible metadata only. It does not claim row counts, refresh freshness, business definitions, primary keys, foreign keys, or join cardinality unless separately validated with data queries.",
        "- Relationship edges are inferred from matching normalized `*Key` column names; treat them as join candidates, not enforced database constraints.",
        "",
        "## Access and Query Guardrails",
        "",
        "- Genie tool is read-only: `SELECT` or `WITH ... SELECT`; data-changing SQL is rejected.",
        "- `SELECT *` is rejected; query only needed fields. Genie caps every page at 20 rows.",
        "- Preferred schemas: `gold` for dimensions/master data and `dv` for business views. `bk_*` views are legacy/backup and should not be the default analytical source.",
        "- Sensitive domains include credit/overdue and customer-identifying fields. Apply least-privilege output and aggregate when possible.",
        "",
        "## Domain Map",
        "",
        "```mermaid",
        "flowchart LR",
        "  D[(LH_OTC_TEST)]",
    ]
    for domain in sorted(domain_objects):
        node_name = "".join(char for char in domain if char.isalnum())
        lines.append(f"  D --> {node_name}[{domain}: {len(domain_objects[domain])} objects]")
    lines += ["```", "", "## Full Object and Field Inventory", ""]

    for domain in sorted(domain_objects):
        lines += [f"### {domain}", ""]
        for obj in sorted(domain_objects[domain], key=object_id):
            obj_id = object_id(obj)
            node = node_by_id[obj_id]
            columns = "; ".join(column_text(column) for column in obj["columns"])
            keys = ", ".join(f"`{key}`" for key in node["key_columns"]) or "None detected"
            lines += [
                f"#### `{obj_id}`",
                "",
                f"- Type: `{obj['type']}` | Columns: {len(obj['columns'])} | Handling: `{node['sensitivity']}`",
                f"- Key-shaped columns: {keys}",
                f"- Fields: {columns}",
                "",
            ]

    lines += ["## Relationship Candidate Rules", "", "- **high**: same `*Key` column name appears in both objects.", "- **candidate**: normalized key names match but casing/underscore form differs.", "- Validate candidate joins with grain, uniqueness, null rate and row-count checks before any metric aggregation.", "", "## Relationship Edge Inventory", ""]
    for edge in edges:
        keys = ", ".join(
            f"{match['source_column']}={match['target_column']}" for match in edge["key_matches"]
        )
        lines.append(f"- `{edge['source']}` <-> `{edge['target']}` via `{keys}` (`{edge['confidence']}` shared-key candidate)")
    GUIDE_PATH.write_text("\n".join(lines) + "\n")


def write_dot(nodes: list[dict], edges: list[dict]) -> None:
    colors = {
        "Sales & OTC": "#3b82f6", "Customer & Segmentation": "#10b981",
        "Product & Brand": "#f59e0b", "Credit & Collection": "#ef4444",
        "Cooler & Equipment": "#06b6d4", "Visit & Execution": "#8b5cf6",
        "Target & Distribution": "#ec4899", "Reference & Operations": "#64748b",
    }
    lines = ["graph FabricKnowledgeGraph {", "  graph [overlap=false, splines=true, bgcolor=\"white\"]", "  node [shape=box, style=\"rounded,filled\", fontname=Arial, fontsize=10]", "  edge [color=\"#94a3b8\", fontsize=8]",]
    for node in nodes:
        color = colors[node["domain"]]
        label = f"{node['id']}\\n{node['column_count']} columns"
        lines.append(f'  "{node["id"]}" [label="{label}", fillcolor="{color}", fontcolor="white"];')
    for edge in edges:
        style = "solid" if edge["confidence"] == "high" else "dashed"
        label = ", ".join(match["source_column"] for match in edge["key_matches"][:3])
        if len(edge["key_matches"]) > 3:
            label += ", ..."
        lines.append(f'  "{edge["source"]}" -- "{edge["target"]}" [label="{label}", style="{style}"];')
    lines.append("}")
    DOT_PATH.write_text("\n".join(lines) + "\n")


def main() -> None:
    catalog = json.loads(CATALOG_PATH.read_text())
    objects = catalog["objects"]
    nodes, edges = build_graph(objects)
    graph = {"database": catalog["database"], "nodes": nodes, "edges": edges}
    GRAPH_PATH.write_text(json.dumps(graph, indent=2))
    write_dot(nodes, edges)
    write_guide(catalog["database"], objects, nodes, edges)
    print(f"Wrote {len(nodes)} nodes and {len(edges)} edges")
    print(GRAPH_PATH)
    print(DOT_PATH)
    print(GUIDE_PATH)


if __name__ == "__main__":
    main()