from whoosh.fields import Schema, TEXT, ID, KEYWORD, STORED
from whoosh.analysis import StemmingAnalyzer
from whoosh.index import create_in, open_dir
from whoosh.qparser import QueryParser, MultifieldParser
from whoosh.query import Term
import os
from typing import List, Dict, Any
from mcp.metadata import ModelMeta, FieldMeta

class ModelIndexer:
    def __init__(self, index_path: str = ".index"):
        self.index_path = index_path
        self.schema = Schema(
            model=ID(stored=True),
            name=TEXT(stored=True),
            module=ID(stored=True),
            field_names=KEYWORD(stored=True),
            field_types=KEYWORD(stored=True),
            field_relations=KEYWORD(stored=True),
            field_help=TEXT(analyzer=StemmingAnalyzer()),
            view_types=KEYWORD(stored=True),
            view_arch=TEXT(analyzer=StemmingAnalyzer()),
            action_names=TEXT(stored=True),
            menu_names=TEXT(stored=True),
            content=TEXT(analyzer=StemmingAnalyzer())
        )
        
        self._ensure_index_dir()
    
    def _ensure_index_dir(self):
        """Ensure the index directory exists"""
        if not os.path.exists(self.index_path):
            os.makedirs(self.index_path)
    
    def create_index(self, models: List[ModelMeta]):
        """Create a new search index from model metadata"""
        ix = create_in(self.index_path, self.schema)
        writer = ix.writer()
        
        for model in models:
            # Collect field information
            field_names = " ".join(f.name for f in model.fields)
            field_types = " ".join(f.type for f in model.fields)
            field_relations = " ".join(f.relation for f in model.fields if f.relation)
            field_help = " ".join(f.help for f in model.fields if f.help)
            
            # Collect view information
            view_types = " ".join(v.view_type for v in model.views)
            view_arch = " ".join(v.arch for v in model.views)
            
            # Collect action and menu information
            action_names = " ".join(a.name for a in model.actions)
            menu_names = " ".join(m.name for m in model.menus)
            
            # Create a rich content field for full-text search
            content = f"{model.model} {model.name or ''} {field_names} {field_help} {view_arch} {action_names} {menu_names}"
            
            writer.add_document(
                model=model.model,
                name=model.name or "",
                module=model.module,
                field_names=field_names,
                field_types=field_types,
                field_relations=field_relations,
                field_help=field_help,
                view_types=view_types,
                view_arch=view_arch,
                action_names=action_names,
                menu_names=menu_names,
                content=content
            )
        
        writer.commit()
    
    def search(self, query_str: str, fields: List[str] = None) -> List[Dict[str, Any]]:
        """Search the index using the given query string"""
        try:
            ix = open_dir(self.index_path)
            
            if fields is None:
                fields = ['model', 'name', 'field_names', 'field_help', 'view_arch', 'action_names', 'menu_names', 'content']
            
            parser = MultifieldParser(fields, ix.schema)
            query = parser.parse(query_str)
            
            results = []
            with ix.searcher() as searcher:
                hits = searcher.search(query, limit=None)
                for hit in hits:
                    results.append({
                        'model': hit['model'],
                        'name': hit['name'],
                        'module': hit['module'],
                        'score': hit.score,
                        'matched_fields': hit.matched_terms()
                    })
            
            return results
        except Exception as e:
            print(f"Error searching index: {e}")
            return []
