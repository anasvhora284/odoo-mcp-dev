from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union

class ViewMeta(BaseModel):
    """Metadata for an Odoo view"""
    view_id: str
    view_type: str
    arch: str
    model: str
    inherit_id: Optional[str] = None
    priority: int = 16

class ActionMeta(BaseModel):
    """Metadata for an Odoo action"""
    action_id: str
    name: str
    type: str
    model: str
    view_mode: str
    domain: Optional[str] = None

class MenuMeta(BaseModel):
    """Metadata for an Odoo menu item"""
    menu_id: str
    name: str
    parent_id: Optional[str] = None
    action: Optional[str] = None
    sequence: int = 10

class FieldMeta(BaseModel):
    """Metadata for an Odoo model field"""
    name: str
    type: str
    relation: Optional[str] = None  # For many2one, one2many, many2many fields
    required: bool = False
    readonly: bool = False
    store: bool = True
    compute: Optional[str] = None
    inverse: Optional[str] = None
    string: Optional[str] = None
    help: Optional[str] = None
    index: Optional[Union[bool, str]] = False  # Can be bool or string like 'btree_not_null'
    copyable: bool = True  # Changed from 'copy' to avoid shadowing BaseModel attribute
    default: Optional[Any] = None
    groups: Optional[str] = None
    states: Optional[Dict[str, Any]] = None

class InheritanceMeta(BaseModel):
    """Metadata for model inheritance"""
    type: str = "class"  # 'class' for _inherit, 'prototype' for _inherits
    parent_model: str
    fields: Optional[Dict[str, str]] = None  # For _inherits: {'field_name': 'parent_model'}

class ModelMeta(BaseModel):
    """Complete metadata for an Odoo model"""
    model: str
    name: Optional[str] = None  # The _description field
    module: str
    is_transient: bool = False  # TransientModel vs Model
    is_abstract: bool = False   # AbstractModel
    fields: List[FieldMeta] = Field(default_factory=list)
    inherits: List[InheritanceMeta] = Field(default_factory=list)
    views: List[ViewMeta] = Field(default_factory=list)
    actions: List[ActionMeta] = Field(default_factory=list)
    menus: List[MenuMeta] = Field(default_factory=list)
