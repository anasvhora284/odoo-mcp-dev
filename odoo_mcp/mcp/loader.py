import os
import yaml
from typing import List, Dict, Optional
from collections import defaultdict
from mcp.parser.python_parser import extract_models_from_python
from mcp.parser.xml_parser import extract_view_metadata
from mcp.metadata import ModelMeta, ViewMeta, ActionMeta, MenuMeta

class ModuleLoader:
    def __init__(self, config_path: str = "config.yaml"):
        self.config = self._load_config(config_path)
        self._loaded_modules = set()  # Track which modules have been loaded
        self.models: Dict[str, ModelMeta] = {}
        self.views: Dict[str, List[ViewMeta]] = defaultdict(list)
        self.actions: Dict[str, List[ActionMeta]] = defaultdict(list)
        self.menus: Dict[str, List[MenuMeta]] = defaultdict(list)
        self._module_paths: Dict[str, str] = {}  # Cache module paths
    
    def _load_config(self, config_path: str) -> dict:
        """Load configuration from YAML file"""
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"Error loading config: {e}")
            return {
                'paths': {
                    'addon_paths': []
                }
            }
    
    def _get_module_name(self, path: str) -> str:
        """Extract module name from file path"""
        parts = path.split(os.sep)
        for i, part in enumerate(parts):
            if part == 'addons' and i + 1 < len(parts):
                return parts[i + 1]
        return os.path.basename(os.path.dirname(path))
    
    def _merge_model_data(self, model: ModelMeta):
        """Merge model data with existing model or create new entry"""
        if model.model in self.models:
            existing = self.models[model.model]
            # Merge fields (avoid duplicates)
            field_names = {f.name for f in existing.fields}
            for field in model.fields:
                if field.name not in field_names:
                    existing.fields.append(field)
            # Merge inheritance
            existing.inherits.extend(model.inherits)
        else:
            self.models[model.model] = model
    
    def load_python_file(self, path: str):
        """Load Python file and extract model information"""
        try:
            with open(path, "r", encoding="utf-8") as f:
                code = f.read()
                module_name = self._get_module_name(path)
                models = extract_models_from_python(code, module_name, path)
                for model in models:
                    self._merge_model_data(model)
        except Exception as e:
            print(f"Error reading Python file {path}: {e}")
    
    def load_xml_file(self, path: str):
        """Load XML file and extract view/action/menu information"""
        try:
            with open(path, "r", encoding="utf-8") as f:
                xml_content = f.read()
                module_name = self._get_module_name(path)
                views, actions, menus = extract_view_metadata(xml_content, module_name)
                
                for view in views:
                    if view.model:
                        self.views[view.model].append(view)
                
                for action in actions:
                    if action.model:
                        self.actions[action.model].append(action)
                        
                for menu in menus:
                    if menu.action:
                        action_ref = menu.action.split('.')[-1]
                        for model, model_actions in self.actions.items():
                            if any(a.action_id.endswith(action_ref) for a in model_actions):
                                self.menus[model].append(menu)
                                break
        except Exception as e:
            print(f"Error reading XML file {path}: {e}")
    
    def load_addons(self, addon_paths: Optional[List[str]] = None) -> List[ModelMeta]:
        """Load all addons from the specified paths"""
        if addon_paths is None:
            addon_paths = self.config['paths']['addon_paths']
        
        for addon_path in addon_paths:
            if not os.path.exists(addon_path):
                print(f"Warning: Addon path {addon_path} does not exist")
                continue
                
            for root, dirs, files in os.walk(addon_path):
                # Skip hidden directories and __pycache__
                dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
                
                for file in files:
                    path = os.path.join(root, file)
                    
                    if file.endswith('.py'):
                        self.load_python_file(path)
                    elif file.endswith('.xml'):
                        self.load_xml_file(path)
        
        # Associate views, actions, and menus with their models
        for model_name, model in self.models.items():
            model.views = self.views.get(model_name, [])
            model.actions = self.actions.get(model_name, [])
            model.menus = self.menus.get(model_name, [])
        
        return list(self.models.values())

    def _discover_modules(self):
        """Discover available modules and their paths"""
        if not self._module_paths:
            addon_paths = self.config['paths']['addon_paths']
            for addon_path in addon_paths:
                if not os.path.exists(addon_path):
                    continue
                    
                for item in os.listdir(addon_path):
                    module_path = os.path.join(addon_path, item)
                    if os.path.isdir(module_path) and not item.startswith('.'):
                        self._module_paths[item] = module_path

    def _load_module(self, module_name: str):
        """Load a specific module"""
        if module_name in self._loaded_modules:
            return
            
        if module_name not in self._module_paths:
            self._discover_modules()
            if module_name not in self._module_paths:
                print(f"Warning: Module {module_name} not found")
                return

        module_path = self._module_paths[module_name]
        
        for root, dirs, files in os.walk(module_path):
            # Skip hidden directories and __pycache__
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
            
            for file in files:
                path = os.path.join(root, file)
                
                if file.endswith('.py'):
                    self.load_python_file(path)
                elif file.endswith('.xml'):
                    self.load_xml_file(path)
        
        self._loaded_modules.add(module_name)

    def load_modules(self, module_names: Optional[List[str]] = None) -> List[ModelMeta]:
        """Load specific modules or all modules if none specified"""
        if not module_names:
            self._discover_modules()
            module_names = list(self._module_paths.keys())
        
        for module_name in module_names:
            self._load_module(module_name)
        
        # Associate views, actions, and menus with their models
        for model_name, model in self.models.items():
            model.views = self.views.get(model_name, [])
            model.actions = self.actions.get(model_name, [])
            model.menus = self.menus.get(model_name, [])
        
        return list(self.models.values())

    def get_module_models(self, module_name: str) -> List[ModelMeta]:
        """Get models for a specific module, loading it if necessary"""
        self._load_module(module_name)
        return [model for model in self.models.values() if model.module == module_name]

def load_addons(addons_path: str) -> List[ModelMeta]:
    """Compatibility function for existing code"""
    loader = ModuleLoader()
    return loader.load_addons([addons_path])
