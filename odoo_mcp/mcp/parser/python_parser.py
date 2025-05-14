import ast
import os
from typing import List, Dict, Any, Optional, Tuple, Union
from mcp.metadata import ModelMeta, FieldMeta, InheritanceMeta, ViewMeta

def _convert_field_value(value: Any) -> Any:
    """Convert field value to appropriate type"""
    if isinstance(value, (ast.Constant, ast.Str)):
        return value.value
    elif isinstance(value, ast.Name):
        if value.id in ('True', 'False'):
            return value.id == 'True'
        return value.id
    elif isinstance(value, ast.Dict):
        result = {}
        for k, v in zip(value.keys, value.values):
            if isinstance(k, ast.Constant) and isinstance(v, ast.Dict):
                state_name = k.value
                state_attrs = {}
                for sk, sv in zip(v.keys, v.values):
                    if isinstance(sk, ast.Constant):
                        state_attrs[sk.value] = _convert_field_value(sv)
                result[state_name] = state_attrs
        return result
    return None

def extract_field_attributes(node: ast.Call) -> Dict[str, Any]:
    """Extract all attributes from a field definition"""
    attrs = {
        'required': False,
        'readonly': False,
        'store': True,
        'index': False,
        'copyable': True
    }
    
    for kw in node.keywords:
        value = _convert_field_value(kw.value)
        if value is not None:
            attrs[kw.arg] = value
    
    return attrs

def extract_models_from_python(code: str, module_name: str, file_path: str) -> List[ModelMeta]:
    models = []

    class Visitor(ast.NodeVisitor):
        def visit_ClassDef(self, node):
            bases = []
            for base in node.bases:
                if isinstance(base, ast.Name):
                    bases.append(base.id)
                elif isinstance(base, ast.Attribute):
                    bases.append(base.attr)
            
            is_model = any(b in ('Model', 'TransientModel', 'AbstractModel') for b in bases)
            
            if is_model:
                fields = []
                model_name = ""
                model_description = ""
                inherits = []
                is_transient = 'TransientModel' in bases
                is_abstract = 'AbstractModel' in bases
                
                for stmt in node.body:
                    if isinstance(stmt, ast.Assign):
                        for target in stmt.targets:
                            if isinstance(target, ast.Name):
                                var_name = target.id
                                
                                # Handle model name and description
                                if var_name == '_name' and isinstance(stmt.value, (ast.Str, ast.Constant)):
                                    model_name = stmt.value.value
                                elif var_name == '_description' and isinstance(stmt.value, (ast.Str, ast.Constant)):
                                    model_description = stmt.value.value
                                elif var_name == '_inherit':
                                    if isinstance(stmt.value, (ast.Str, ast.Constant)):
                                        inherits.append(InheritanceMeta(
                                            type='class',
                                            parent_model=stmt.value.value
                                        ))
                                    elif isinstance(stmt.value, ast.List):
                                        for elt in stmt.value.elts:
                                            if isinstance(elt, (ast.Str, ast.Constant)):
                                                inherits.append(InheritanceMeta(
                                                    type='class',
                                                    parent_model=elt.value
                                                ))
                                elif var_name == '_inherits':
                                    if isinstance(stmt.value, ast.Dict):
                                        for k, v in zip(stmt.value.keys, stmt.value.values):
                                            if isinstance(k, (ast.Str, ast.Constant)) and isinstance(v, (ast.Str, ast.Constant)):
                                                inherits.append(InheritanceMeta(
                                                    type='prototype',
                                                    parent_model=k.value,
                                                    fields={v.value: k.value}
                                                ))
                                
                                # Handle fields
                                if isinstance(stmt.value, ast.Call):
                                    if (hasattr(stmt.value.func, 'value') and 
                                        isinstance(stmt.value.func.value, ast.Name) and 
                                        stmt.value.func.value.id == 'fields'):
                                        
                                        field_type = stmt.value.func.attr
                                        field_attrs = extract_field_attributes(stmt.value)
                                        
                                        try:
                                            field = FieldMeta(
                                                name=var_name,
                                                type=field_type,
                                                relation=field_attrs.get('comodel_name'),
                                                required=field_attrs.get('required', False),
                                                readonly=field_attrs.get('readonly', False),
                                                store=field_attrs.get('store', True),
                                                compute=field_attrs.get('compute'),
                                                inverse=field_attrs.get('inverse'),
                                                string=field_attrs.get('string'),
                                                help=field_attrs.get('help'),
                                                index=field_attrs.get('index', False),
                                                copyable=field_attrs.get('copyable', True),
                                                groups=field_attrs.get('groups'),
                                                states=field_attrs.get('states')
                                            )
                                            fields.append(field)
                                        except Exception as e:
                                            print(f"Error creating field {var_name}: {e}")
                                        fields.append(field)
                
                if model_name:
                    models.append(ModelMeta(
                        model=model_name,
                        name=model_description,
                        module=module_name,
                        is_transient=is_transient,
                        is_abstract=is_abstract,
                        fields=fields,
                        inherits=inherits
                    ))

    tree = ast.parse(code)
    Visitor().visit(tree)
    return models
