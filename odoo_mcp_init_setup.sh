#!/bin/bash

# Create the directory structure first
mkdir -p odoo_mcp/{mcp/{parser,indexer,api},scripts}

# Create requirements.txt
cat > odoo_mcp/requirements.txt << 'EOF'
fastapi
uvicorn
whoosh
lxml
pydantic
EOF

# Create mcp/metadata.py
cat > odoo_mcp/mcp/metadata.py << 'EOF'
from pydantic import BaseModel
from typing import List

class FieldMeta(BaseModel):
    name: str
    type: str

class ModelMeta(BaseModel):
    model: str
    fields: List[FieldMeta]
EOF

# Create mcp/parser/python_parser.py
cat > odoo_mcp/mcp/parser/python_parser.py << 'EOF'
import ast
from mcp.metadata import ModelMeta, FieldMeta

def extract_models_from_python(code: str) -> list[ModelMeta]:
    models = []

    class Visitor(ast.NodeVisitor):
        def visit_ClassDef(self, node):
            bases = [b.id if isinstance(b, ast.Name) else getattr(b, 'attr', '') for b in node.bases]
            if 'Model' in bases or 'osv' in bases:
                fields = []
                model_name = ""
                for stmt in node.body:
                    if isinstance(stmt, ast.Assign):
                        for target in stmt.targets:
                            if isinstance(target, ast.Name):
                                fname = target.id
                                if fname == '_name' and isinstance(stmt.value, ast.Str):
                                    model_name = stmt.value.s
                                if isinstance(stmt.value, ast.Call):
                                    if hasattr(stmt.value.func, 'value') and stmt.value.func.value.id == 'fields':
                                        ftype = stmt.value.func.attr
                                        fields.append(FieldMeta(name=fname, type=ftype))
                if model_name:
                    models.append(ModelMeta(model=model_name, fields=fields))

    tree = ast.parse(code)
    Visitor().visit(tree)
    return models
EOF

# Create mcp/parser/xml_parser.py
cat > odoo_mcp/mcp/parser/xml_parser.py << 'EOF'
from lxml import etree

def extract_fields_from_view(xml_str: str) -> list[str]:
    try:
        tree = etree.fromstring(xml_str.encode())
        fields = tree.xpath("//field[@name]")
        return list({f.get("name") for f in fields})
    except Exception as e:
        return []
EOF

# Create mcp/loader.py
cat > odoo_mcp/mcp/loader.py << 'EOF'
import os
from mcp.parser.python_parser import extract_models_from_python

def load_addons(addons_path: str):
    model_data = []

    for root, dirs, files in os.walk(addons_path):
        for file in files:
            if file.endswith(".py"):
                path = os.path.join(root, file)
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        code = f.read()
                        models = extract_models_from_python(code)
                        if models:
                            model_data.extend(models)
                except Exception as e:
                    print(f"Error reading {path}: {e}")

    return model_data
EOF

# Create mcp/indexer/whoosh_indexer.py
cat > odoo_mcp/mcp/indexer/whoosh_indexer.py << 'EOF'
from whoosh.fields import Schema, TEXT, ID
from whoosh.index import create_in, open_dir
from whoosh.qparser import QueryParser
import os

def create_search_index(index_dir="whoosh_index"):
    if not os.path.exists(index_dir):
        os.mkdir(index_dir)
    schema = Schema(path=ID(stored=True), content=TEXT)
    return create_in(index_dir, schema)

def index_file(ix, path, content):
    writer = ix.writer()
    writer.add_document(path=path, content=content)
    writer.commit()

def search_index(ix, query_str):
    qp = QueryParser("content", schema=ix.schema)
    q = qp.parse(query_str)
    with ix.searcher() as searcher:
        results = searcher.search(q)
        return [r['path'] for r in results]
EOF

# Create mcp/api/routes.py
cat > odoo_mcp/mcp/api/routes.py << 'EOF'
from fastapi import APIRouter
from mcp.metadata import ModelMeta
from mcp.loader import load_addons

router = APIRouter()
MODELS = []

@router.on_event("startup")
def startup_event():
    global MODELS
    MODELS = load_addons("YOUR_DEFAULT_ODOO_ADDONS_PATH")

@router.get("/models")
def get_all_models():
    return [m.model for m in MODELS]

@router.get("/models/{model_name}", response_model=ModelMeta)
def get_model(model_name: str):
    for m in MODELS:
        if m.model == model_name:
            return m
    return {"error": "not found"}
EOF

# Create main.py
cat > odoo_mcp/main.py << 'EOF'
from fastapi import FastAPI
from mcp.api.routes import router

app = FastAPI(title="Odoo MCP API")
app.include_router(router)
EOF

# Create scripts/scan_odoo.py
cat > odoo_mcp/scripts/scan_odoo.py << 'EOF'
import sys
from mcp.loader import load_addons

if __name__ == "__main__":
    path = sys.argv[1]
    models = load_addons(path)
    for m in models:
        print(f"Model: {m.model}")
        for f in m.fields:
            print(f"  - {f.name} ({f.type})")
EOF

# Create an empty config.yaml
touch odoo_mcp/config.yaml

# Create __init__.py files
touch odoo_mcp/mcp/__init__.py
touch odoo_mcp/mcp/parser/__init__.py
touch odoo_mcp/mcp/indexer/__init__.py
touch odoo_mcp/mcp/api/__init__.py

# Make script executable
chmod +x odoo_mcp/scripts/scan_odoo.py

echo "Successfully populated odoo_mcp directory with code!"