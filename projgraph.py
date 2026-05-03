#!/usr/bin/env python3

import argparse
import yaml
from pathlib import Path
from collections import defaultdict, deque

def load_nodes(base_dir):
    nodes = {}
    for md_file in Path(base_dir).rglob("*.md"):
        content = md_file.read_text()

        if content.startswith("---"):
            frontmatter = content.split("---")[1]
            data = yaml.safe_load(frontmatter)

            if "id" in data:
                nid = data["id"]
                nodes[nid] = {
                    "duration": data.get("duration", 1),
                    "depends_on": data.get("depends_on", []),
                    "label": md_file.stem.replace("_", " ").title(),
                    "project": data.get("project", "default"),
                }
    return nodes

def build_graph(nodes):
    graph = defaultdict(list)
    reverse = defaultdict(list)

    for nid, node in nodes.items():
        for dep in node["depends_on"]:
            graph[dep].append(nid)
            reverse[nid].append(dep)

    return graph, reverse

def topo_sort(nodes, reverse):
    in_degree = {nid: len(reverse[nid]) for nid in nodes}

    queue = deque([n for n in nodes if in_degree[n] == 0])
    topo = []

    while queue:
        n = queue.popleft()
        topo.append(n)
        for child in [c for c in nodes if n in nodes[c]["depends_on"]]:
            in_degree[child] -= 1
            if in_degree[child] == 0:
                queue.append(child)

    return topo

def compute_cpm(nodes, graph, reverse):
    topo = topo_sort(nodes, reverse)

    ES, EF = {}, {}

    for n in topo:
        if not reverse[n]:
            ES[n] = 0
        else:
            ES[n] = max(EF[d] for d in reverse[n])
        EF[n] = ES[n] + nodes[n]["duration"]

    project_duration = max(EF.values())

    LS, LF = {}, {}

    for n in reversed(topo):
        if not graph[n]:
            LF[n] = project_duration
        else:
            LF[n] = min(LS[c] for c in graph[n])
        LS[n] = LF[n] - nodes[n]["duration"]

    slack = {n: LS[n] - ES[n] for n in nodes}
    critical = [n for n in nodes if slack[n] == 0]

    return ES, EF, LS, LF, slack, critical, project_duration

def generate_mermaid(nodes, graph, critical, output_file):
    lines = ["graph LR"]

    for nid, node in nodes.items():
        label = f"{node['label']} ({node['duration']}d)"
        lines.append(f'{nid}["{label}"]')

    for nid, node in nodes.items():
        for dep in node["depends_on"]:
            lines.append(f"{dep} --> {nid}")

    lines.append("classDef critical fill:#ff6666,stroke:#aa0000;")
    for nid in critical:
        lines.append(f"class {nid} critical")

    Path(output_file).write_text("\n".join(lines))

def simulate_delay(nodes, target, delay, compute_fn):
    original = nodes[target]["duration"]
    nodes[target]["duration"] += delay

    graph, reverse = build_graph(nodes)
    _, _, _, _, _, _, new_duration = compute_fn(nodes, graph, reverse)

    nodes[target]["duration"] = original
    return new_duration

def main():
    parser = argparse.ArgumentParser(description="Project Dependency Graph Tool")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", default="graph.mermaid")
    parser.add_argument("--delay-node")
    parser.add_argument("--delay-days", type=int, default=0)

    args = parser.parse_args()

    nodes = load_nodes(args.input)
    graph, reverse = build_graph(nodes)

    ES, EF, LS, LF, slack, critical, duration = compute_cpm(nodes, graph, reverse)

    print("\n=== PROJECT SUMMARY ===")
    print("Total Duration:", duration)
    print("Critical Path:", " -> ".join(critical))

    print("\nNode Details:")
    for n in nodes:
        print(f"{n}: ES={ES[n]}, EF={EF[n]}, Slack={slack[n]}")

    generate_mermaid(nodes, graph, critical, args.output)
    print(f"\nMermaid written to {args.output}")

    if args.delay_node:
        new_duration = simulate_delay(nodes, args.delay_node, args.delay_days, compute_cpm)
        print("\n=== DELAY SIMULATION ===")
        print(f"Node: {args.delay_node}")
        print(f"Delay: +{args.delay_days} days")
        print(f"New Duration: {new_duration}")
        print(f"Impact: +{new_duration - duration}")

if __name__ == "__main__":
    main()