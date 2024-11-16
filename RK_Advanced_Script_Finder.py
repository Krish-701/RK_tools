import os
import sys
import json
import inspect
import logging
import traceback
import numpy as np
import torch
from PIL import Image

class RK_Advanced_Script_Finder:
    def __init__(self):
        self.node_list = []
        self.custom_node_list = []
        self.update_node_list()

    def update_node_list(self):
        """Scan and update the list of available nodes in ComfyUI"""
        try:
            import nodes
            self.node_list = []
            self.custom_node_list = []
            
            for node_name, node_class in nodes.NODE_CLASS_MAPPINGS.items():
                try:
                    # Determine if it's a custom node
                    module = inspect.getmodule(node_class)
                    module_path = getattr(module, '__file__', '')
                    is_custom = 'custom_nodes' in module_path

                    node_info = {
                        'name': node_name,
                        'class_name': node_class.__name__,
                        'category': getattr(node_class, 'CATEGORY', 'Uncategorized'),
                        'description': getattr(node_class, 'DESCRIPTION', ''),
                        'is_custom': is_custom
                    }
                    
                    self.node_list.append(node_info)
                    if is_custom:
                        self.custom_node_list.append(node_info)
                except Exception as e:
                    logging.error(f"Error processing node {node_name}: {str(e)}")
                    continue
            
            # Sort nodes alphabetically
            self.node_list.sort(key=lambda x: x['name'])
            self.custom_node_list.sort(key=lambda x: x['name'])
            
        except Exception as e:
            logging.error(f"Error updating node list: {str(e)}")
            traceback.print_exc()

    @classmethod
    def INPUT_TYPES(cls):
        try:
            import nodes
            node_names = sorted(list(nodes.NODE_CLASS_MAPPINGS.keys()))
            if not node_names:
                node_names = ["No nodes found"]
                
            return {
                "required": {
                    "mode": (["All Nodes", "Custom Nodes Only", "Built-in Nodes Only"], {
                        "default": "All Nodes"
                    }),
                    "view_mode": (["List Nodes", "View Source Code", "Usage Guide"], {
                        "default": "List Nodes"
                    }),
                    "selected_node": (node_names, {
                        "default": node_names[0]
                    }),
                    "search": ("STRING", {
                        "default": "",
                        "multiline": False
                    }),
                    "show_all": ("BOOLEAN", {
                        "default": True,
                        "label": "Show All Nodes"
                    }),
                    "refresh_list": ("BOOLEAN", {
                        "default": False,
                        "label": "Refresh Node List"
                    })
                }
            }
        except Exception as e:
            print(f"Error in INPUT_TYPES: {str(e)}")
            return {
                "required": {
                    "mode": (["All Nodes", "Custom Nodes Only", "Built-in Nodes Only"], {"default": "All Nodes"}),
                    "view_mode": (["List Nodes", "View Source Code", "Usage Guide"], {"default": "List Nodes"}),
                    "search": ("STRING", {"default": "", "multiline": False}),
                    "show_all": ("BOOLEAN", {"default": True, "label": "Show All Nodes"}),
                    "refresh_list": ("BOOLEAN", {"default": False, "label": "Refresh Node List"})
                }
            }

    RETURN_TYPES = ("STRING", "STRING",)
    RETURN_NAMES = ("node_info", "node_source",)
    FUNCTION = "find_script"
    CATEGORY = "RK/utils"

    def get_node_source_code(self, node_name):
        """Get the source code of a node"""
        try:
            import nodes
            import inspect
            import os

            # Get the node class
            node_class = nodes.NODE_CLASS_MAPPINGS.get(node_name)
            if not node_class:
                return f"Node '{node_name}' not found"

            # Get the module
            module = inspect.getmodule(node_class)
            if not module:
                return f"Could not find module for {node_name}"

            # Get file path
            try:
                file_path = inspect.getfile(module)
            except TypeError:
                return f"Could not determine file path for {node_name}"

            # Read entire file content
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    file_content = f.read()
            except Exception as e:
                return f"Error reading file: {str(e)}"

            # Find the class definition
            class_def = f"class {node_class.__name__}:"
            class_start = file_content.find(class_def)
            
            if class_start == -1:
                return f"Could not find class definition for {node_name}"

            # Extract class source code
            lines = file_content[class_start:].split('\n')
            class_lines = []
            indent_level = None

            for line in lines:
                # Determine initial indent level
                if indent_level is None:
                    if line.strip().startswith('class'):
                        indent_level = len(line) - len(line.lstrip())
                    continue

                # Check if we've reached the end of the class
                current_indent = len(line) - len(line.lstrip())
                if current_indent <= indent_level and line.strip():
                    break

                class_lines.append(line)

            # Construct formatted output
            source_output = f"=== Node: {node_name} ===\n"
            source_output += f"File: {file_path}\n\n"
            source_output += "=== Source Code ===\n"
            source_output += "\n".join(class_lines)

            return source_output

        except Exception as e:
            return f"Error retrieving source code: {str(e)}"

    def find_script(self, mode, view_mode, selected_node, search, show_all, refresh_list):
        """Main function to find and return selected node"""
        try:
            # Refresh node list if requested
            if refresh_list:
                self.update_node_list()

            # Handle source code view mode
            if view_mode == "View Source Code":
                if selected_node:
                    source_code = self.get_node_source_code(selected_node)
                    return f"Source Code for {selected_node}", source_code
                return "No node selected", "Please select a node to view its source code"

            # Default fallback
            return "Node Source Finder", "Select a node and choose 'View Source Code' mode"

        except Exception as e:
            logging.error(f"Error in find_script: {str(e)}")
            traceback.print_exc()
            return f"Error: {str(e)}", traceback.format_exc()

# Register the node in ComfyUI
NODE_CLASS_MAPPINGS = {
    "RK_Advanced_Script_Finder": RK_Advanced_Script_Finder
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "RK_Advanced_Script_Finder": "RK Advanced Script Finder"
}