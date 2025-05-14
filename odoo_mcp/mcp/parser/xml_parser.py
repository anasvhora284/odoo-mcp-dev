from lxml import etree
from typing import List, Dict, Optional, Tuple
from mcp.metadata import ViewMeta, ActionMeta, MenuMeta

def extract_view_metadata(xml_str: str, module: str) -> Tuple[List[ViewMeta], List[ActionMeta], List[MenuMeta]]:
    """Extract view, action and menu metadata from XML file"""
    views = []
    actions = []
    menus = []
    
    try:
        tree = etree.fromstring(xml_str.encode())
        
        # Process views
        for record in tree.xpath("//record[@model='ir.ui.view']"):
            view_id = record.get('id', '')
            fields = {child.get('name'): child for child in record.xpath(".//field")}
            
            if 'arch' in fields and 'model' in fields:
                arch = fields['arch']
                if isinstance(arch.text, str):
                    arch_str = arch.text
                else:
                    arch_str = etree.tostring(arch[0] if arch else arch, encoding='unicode')
                
                view = ViewMeta(
                    view_id=f"{module}.{view_id}",
                    model=fields['model'].text or '',
                    view_type=fields.get('type', etree.Element('field')).text or 'form',
                    arch=arch_str,
                    inherit_id=fields.get('inherit_id', etree.Element('field')).get('ref'),
                    priority=int(fields.get('priority', etree.Element('field')).text or '16')
                )
                views.append(view)
        
        # Process actions
        for record in tree.xpath("//record[@model='ir.actions.act_window']"):
            action_id = record.get('id', '')
            fields = {child.get('name'): child for child in record.xpath(".//field")}
            
            if 'res_model' in fields:
                action = ActionMeta(
                    action_id=f"{module}.{action_id}",
                    name=fields.get('name', etree.Element('field')).text or '',
                    type='ir.actions.act_window',
                    model=fields['res_model'].text or '',
                    view_mode=fields.get('view_mode', etree.Element('field')).text or 'tree,form',
                    domain=fields.get('domain', etree.Element('field')).text
                )
                actions.append(action)
        
        # Process menus
        for record in tree.xpath("//record[@model='ir.ui.menu']"):
            menu_id = record.get('id', '')
            fields = {child.get('name'): child for child in record.xpath(".//field")}
            
            menu = MenuMeta(
                menu_id=f"{module}.{menu_id}",
                name=fields.get('name', etree.Element('field')).text or '',
                parent_id=fields.get('parent_id', etree.Element('field')).get('ref'),
                action=fields.get('action', etree.Element('field')).get('ref'),
                sequence=int(fields.get('sequence', etree.Element('field')).text or '10')
            )
            menus.append(menu)
            
    except Exception as e:
        print(f"Error parsing XML: {e}")
    
    return views, actions, menus

def extract_fields_from_view(xml_str: str) -> List[str]:
    """Extract field names from view architecture"""
    try:
        tree = etree.fromstring(xml_str.encode())
        fields = tree.xpath("//field[@name]")
        return list({f.get("name") for f in fields})
    except Exception as e:
        print(f"Error extracting fields from view: {e}")
        return []
