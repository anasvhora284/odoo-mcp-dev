from fastapi import APIRouter, Query, Depends
from pydantic import BaseModel
from typing import Union, List, Optional, Dict, Any
import os
import yaml

from mcp.loader import ModuleLoader
from mcp import metadata
from mcp.indexer.whoosh_indexer import ModelIndexer

router = APIRouter()
loader = None
indexer = None


class ErrorResponse(BaseModel):
    error: str


class SearchResult(BaseModel):
    model: str
    name: str
    module: str
    score: float
    matched_fields: List[tuple]


def get_config():
    try:
        with open("config.yaml", 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"Error loading config: {e}")
        return {"paths": {"addon_paths": []}}


@router.on_event("startup")
async def startup_event():
    global loader, indexer
    config = get_config()
    
    # Initialize loader
    loader = ModuleLoader("config.yaml")
    
    # Initialize indexer
    indexer = ModelIndexer(config.get('indexing', {}).get('path', '.index'))
    
    # Only discover modules initially, don't load them
    loader._discover_modules()
    
    # Create empty search index if enabled
    if config.get('indexing', {}).get('enabled', True):
        indexer.create_index([])


@router.get("/modules")
async def get_all_modules(
    include_translations: bool = Query(False, description="Include l10n and i18n translation modules"),
    include_tests: bool = Query(False, description="Include test modules")
):
    """List all available modules with optional filters for translations and test modules"""
    loader._discover_modules()
    modules = loader._module_paths.keys()
    
    filtered_modules = []
    for module in modules:
        # Skip translation modules unless explicitly requested
        if not include_translations and (module.startswith(('l10n_', 'i18n_'))):
            continue
            
        # Skip test modules unless explicitly requested
        if not include_tests and ('test' in module.lower()):
            continue
            
        filtered_modules.append(module)
    
    return sorted(filtered_modules)


@router.get("/models", response_model=List[str])
async def get_all_models(module: Optional[str] = None):
    """List all available model names, optionally filtered by module"""
    if module:
        models = loader.get_module_models(module)
    else:
        models = loader.models.values()
    return sorted(set(m.model for m in models))


@router.get("/models/{model_name}", response_model=Union[metadata.ModelMeta, ErrorResponse])
async def get_model(model_name: str, load_module: bool = True):
    """Get detailed metadata for a specific model"""
    # If model isn't loaded and load_module is True, try to find and load its module
    if model_name not in loader.models and load_module:
        # Search through modules until we find it
        loader._discover_modules()
        for module in loader._module_paths:
            loader._load_module(module)
            if model_name in loader.models:
                break
    
    if model_name in loader.models:
        return loader.models[model_name]
    return ErrorResponse(error="Model not found")


@router.get("/search", response_model=List[SearchResult])
async def search_models(
    q: str = Query(..., description="Search query string"),
    fields: Optional[List[str]] = Query(None, description="Fields to search in")
):
    """Full-text search across models, fields, views, and metadata"""
    if not indexer:
        return ErrorResponse(error="Search index not available")
    
    results = indexer.search(q, fields)
    # Remove duplicates based on model name
    seen = set()
    unique_results = []
    for result in sorted(results, key=lambda x: (-x['score'], x['model'])):
        if result['model'] not in seen:
            seen.add(result['model'])
            unique_results.append(SearchResult(**result))
    return unique_results


@router.get("/models/{model_name}/fields", response_model=List[metadata.FieldMeta])
async def get_model_fields(model_name: str):
    """Get all fields for a specific model"""
    if model_name in loader.models:
        # Return unique fields based on field name
        fields = loader.models[model_name].fields
        seen = set()
        unique_fields = []
        for field in sorted(fields, key=lambda x: x.name):
            if field.name not in seen:
                seen.add(field.name)
                unique_fields.append(field)
        return unique_fields
    return ErrorResponse(error="Model not found")


@router.get("/models/{model_name}/views", response_model=List[metadata.ViewMeta])
async def get_model_views(model_name: str):
    """Get all views associated with a specific model"""
    if model_name in loader.models:
        # Return unique views based on view_id
        views = loader.models[model_name].views
        seen = set()
        unique_views = []
        for view in sorted(views, key=lambda x: (x.priority, x.view_id)):
            if view.view_id not in seen:
                seen.add(view.view_id)
                unique_views.append(view)
        return unique_views
    return ErrorResponse(error="Model not found")


@router.get("/models/{model_name}/actions", response_model=List[metadata.ActionMeta])
async def get_model_actions(model_name: str):
    """Get all actions associated with a specific model"""
    if model_name in loader.models:
        # Return unique actions based on action_id
        actions = loader.models[model_name].actions
        seen = set()
        unique_actions = []
        for action in sorted(actions, key=lambda x: x.action_id):
            if action.action_id not in seen:
                seen.add(action.action_id)
                unique_actions.append(action)
        return unique_actions
    return ErrorResponse(error="Model not found")


@router.get("/models/{model_name}/menus", response_model=List[metadata.MenuMeta])
async def get_model_menus(model_name: str):
    """Get all menu items associated with a specific model"""
    if model_name in loader.models:
        # Return unique menus based on menu_id
        menus = loader.models[model_name].menus
        seen = set()
        unique_menus = []
        for menu in sorted(menus, key=lambda x: (x.sequence, x.menu_id)):
            if menu.menu_id not in seen:
                seen.add(menu.menu_id)
                unique_menus.append(menu)
        return unique_menus
    return ErrorResponse(error="Model not found")
