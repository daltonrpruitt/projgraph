# projgraph
CLI tool to translate files conforming to a YAML spec into Mermaid graphs for analyzing dependencies

This tool will:
- Parse Markdown files with YAML frontmatter
- Build dependency graph (DAG)
- Compute critical path
- Simulate delays
- Output:
- Mermaid diagram
- Console summary