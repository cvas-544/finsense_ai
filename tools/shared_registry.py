"""
Script Name: shared_registry.py
Author: Vasu Chukka
Created: 2025-04-19
Last Modified: 2025-04-19
Description: Provides a registry system for tools and actions, enabling dynamic metadata management and execution.
"""

import inspect
import json
from typing import Callable, Dict, List, get_type_hints

# Global registries to store tools and tools categorized by tags
tools = {}
tools_by_tag = {}

# Helper function to map Python types to JSON schema types
def get_json_type(py_type):
    if py_type == str:
        return "string"
    if py_type == int:
        return "integer"
    if py_type == float:
        return "number"
    if py_type == bool:
        return "boolean"
    if py_type == list:
        return "array"
    if py_type == dict:
        return "object"
    return "string"  # Default to string if type is unknown

# Function to generate metadata for a tool
def get_tool_metadata(func, tool_name=None, description=None, parameters_override=None, terminal=False, tags=None):
    # Use the function name as the tool name if not provided
    tool_name = tool_name or func.__name__
    # Use the function's docstring as the description if not provided
    description = description or (func.__doc__ or "No description provided.").strip()

    # If no parameter schema override is provided, infer it from the function signature
    if parameters_override is None:
        signature = inspect.signature(func)  # Get the function's signature
        type_hints = get_type_hints(func)  # Get type hints for the function

        # Initialize the JSON schema for the function's parameters
        args_schema = {
            "type": "object",
            "properties": {},
            "required": []
        }

        # Iterate over the function's parameters
        for param_name, param in signature.parameters.items():
            # Skip special parameters like "action_context" and "action_agent"
            if param_name in ["action_context", "action_agent"]:
                continue
            # Get the parameter type or default to string
            param_type = type_hints.get(param_name, str)
            # Add the parameter to the schema
            args_schema["properties"][param_name] = {
                "type": get_json_type(param_type)
            }
            # Mark the parameter as required if it has no default value
            if param.default == inspect.Parameter.empty:
                args_schema["required"].append(param_name)
    else:
        # Use the provided parameter schema override
        args_schema = parameters_override

    # Return the metadata dictionary for the tool
    return {
        "tool_name": tool_name,
        "description": description,
        "parameters": args_schema,
        "function": func,
        "terminal": terminal,
        "tags": tags or []  # Default to an empty list if no tags are provided
    }

# Decorator to register a function as a tool
def register_tool(tool_name=None, description=None, parameters_override=None, terminal=False, tags=None):
    def decorator(func):
        print(f"🔧 Registering tool: {func.__name__}")
        # Generate metadata for the tool
        metadata = get_tool_metadata(func, tool_name, description, parameters_override, terminal, tags)
        # Add the tool to the global registry
        tools[metadata["tool_name"]] = {
            "description": metadata["description"],
            "parameters": metadata["parameters"],
            "function": metadata["function"],
            "terminal": metadata["terminal"],
            "tags": metadata["tags"]
        }

        # Add the tool to the tag-based registry
        for tag in metadata["tags"]:
            tools_by_tag.setdefault(tag, []).append(metadata["tool_name"])

        return func  # Return the original function
    return decorator

# Class representing an action with metadata and execution logic
class Action:
    def __init__(self, name, function, description, parameters, terminal=False):
        self.name = name  # Name of the action
        self.function = function  # Function to execute
        self.description = description  # Description of the action
        self.parameters = parameters  # Parameters schema
        self.terminal = terminal  # Whether the action is terminal

    # Execute the action with the provided arguments
    def execute(self, **kwargs):
        return self.function(**kwargs)

# Registry to manage actions
class ActionRegistry:
    def __init__(self):
        self.actions = {}  # Dictionary to store actions by name

    # Register a new action in the registry
    def register(self, action: Action):
        self.actions[action.name] = action

    # Retrieve an action by name
    def get_action(self, name: str):
        return self.actions.get(name)

    # Retrieve all registered actions
    def get_actions(self):
        return list(self.actions.values())

# Specialized registry for Python-based actions
class PythonActionRegistry(ActionRegistry):
    def __init__(self, tags: List[str] = None):
        super().__init__()  # Initialize the base ActionRegistry

        # Register tools as actions, optionally filtering by tags
        for tool_name, desc in tools.items():
            # Skip tools that don't match the specified tags
            if tags and not any(t in desc.get("tags", []) for t in tags):
                continue

            # Register the tool as an action
            self.register(Action(
                name=tool_name,
                function=desc["function"],
                description=desc["description"],
                parameters=desc["parameters"],
                terminal=desc.get("terminal", False)
            ))
