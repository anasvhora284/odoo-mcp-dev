import sys
from mcp.loader import load_addons

if __name__ == "__main__":
    path = sys.argv[1]
    models = load_addons(path)
    for m in models:
        print(f"Model: {m.model}")
        for f in m.fields:
            print(f"  - {f.name} ({f.type})")
