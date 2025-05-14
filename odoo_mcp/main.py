import click
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mcp.api.routes import router
import yaml
import os
from typing import Optional

app = FastAPI(
    title="Odoo MCP API",
    description="Model Context Protocol API for Odoo",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(router, prefix="/api/v1")


@click.group()
def cli():
    """Odoo Model Context Protocol (MCP) CLI"""
    pass


@cli.command()
@click.option('--host', default='0.0.0.0', help='Host to bind to')
@click.option('--port', default=8000, help='Port to bind to')
@click.option('--reload', is_flag=True, help='Enable auto-reload on code changes')
def serve(host: str, port: int, reload: bool):
    """Start the MCP API server"""
    uvicorn.run("main:app", host=host, port=port, reload=reload)


@cli.command()
@click.argument('odoo_path', type=click.Path(exists=True))
@click.option('--output', '-o', type=click.Path(), help='Output file for indexed data')
def index(odoo_path: str, output: Optional[str]):
    """Index an Odoo installation"""
    from mcp.loader import ModuleLoader
    from mcp.indexer.whoosh_indexer import ModelIndexer
    
    config = {
        'paths': {
            'odoo_path': odoo_path,
            'addon_paths': [
                os.path.join(odoo_path, 'addons'),
                os.path.join(odoo_path, 'odoo', 'addons')
            ]
        },
        'indexing': {
            'enabled': True,
            'path': output or '.index'
        }
    }
    
    with open('config.yaml', 'w') as f:
        yaml.dump(config, f)
    
    loader = ModuleLoader('config.yaml')
    models = loader.load_addons()
    
    click.echo(f"Found {len(models)} models")
    
    if config['indexing']['enabled']:
        indexer = ModelIndexer(config['indexing']['path'])
        indexer.create_index(models)
        click.echo(f"Created search index at {config['indexing']['path']}")


@cli.command()
@click.argument('query')
def search(query: str):
    """Search indexed Odoo models"""
    from mcp.indexer.whoosh_indexer import ModelIndexer
    
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    index_path = config.get('indexing', {}).get('path', '.index')
    indexer = ModelIndexer(index_path)
    
    results = indexer.search(query)
    
    if not results:
        click.echo("No results found")
        return
    
    for result in results:
        click.echo(f"\nModel: {result['model']}")
        if result['name']:
            click.echo(f"Name: {result['name']}")
        click.echo(f"Module: {result['module']}")
        click.echo(f"Score: {result['score']:.2f}")


if __name__ == '__main__':
    cli()
