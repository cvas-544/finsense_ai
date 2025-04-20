"""
Script Name: base.py
Author: Vasu Chukka
Created: 2025-04-19
Last Modified: 2025-04-19
Description: Defines the foundation components for building and AI agent system.
"""

import json
from typing import List, Dict, Callable, Any
from dataclasses import dataclass
from tools.shared_registry import ActionRegistry, Action
from memory.memory_store import Memory
from environment.budgeting_env import BudgetingEnvironment

# Represents a goal with a priority, name, and description
@dataclass(frozen=True)
class Goal:
    priority: int
    name: str
    description: str

# Represents a prompt with messages, tools, and optional metadata
@dataclass
class Prompt:
    messages: List[Dict]
    tools: List[Dict]
    metadata: Dict = None

# Abstract class for defining agent language behavior
class AgentLanguage:
    # Constructs a prompt based on goals, actions, memory, and environment
    def construct_prompt(self, goals, actions, memory, environment):
        raise NotImplementedError

    # Parses the response from the agent
    def parse_response(self, response: str):
        raise NotImplementedError

# Base class for an AI agent
class BaseAgent:
    def __init__(self,
                 goals: List[Goal],  # List of goals for the agent
                 agent_language: AgentLanguage,  # Language model interface
                 action_registry: ActionRegistry,  # Registry of available actions
                 generate_response: Callable[[Prompt], str],  # Function to generate responses
                 environment: BudgetingEnvironment):  # Environment in which the agent operates
        self.goals = goals
        self.agent_language = agent_language
        self.actions = action_registry
        self.generate_response = generate_response
        self.environment = environment

    # Constructs a prompt for the language model
    def construct_prompt(self, goals, memory, actions):
        return self.agent_language.construct_prompt(
            actions=actions.get_actions(),  # Retrieve available actions
            environment=self.environment,  # Pass the environment
            goals=goals,  # Include the goals
            memory=memory  # Include the memory
        )

    # Determines the action to take based on the response
    # def get_action(self, response):
    #     invocation = self.agent_language.parse_response(response)  # Parse the response
    #     action = self.actions.get_action(invocation["tool"])  # Get the corresponding action
    #     return action, invocation
    def get_action(self, response):
        invocation = self.agent_language.parse_response(response) # Parse the response
        tool_name = invocation["tool"] # Get the corresponding action
        print(f"🔧 Tool selected by LLM: {tool_name}")
        action = self.actions.get_action(tool_name)
        return action, invocation

    # Checks if the agent should terminate based on the response
    def should_terminate(self, response: str) -> bool:
        action_def, _ = self.get_action(response)
        if not action_def:
            print("⚠️ Unknown tool — treating as terminal.")
            return True
        return action_def.terminal

    # Sets the current task in memory
    def set_current_task(self, memory: Memory, task: str):
        memory.add_memory({"type": "user", "content": task})  # Add user task to memory

    # Updates the memory with the response and result
    def update_memory(self, memory: Memory, response: str, result: dict):
        memory.add_memory({"type": "assistant", "content": response})  # Add assistant response
        memory.add_memory({"type": "environment", "content": json.dumps(result)})  # Add environment result

    # Prompts the language model for an action
    def prompt_llm_for_action(self, full_prompt: Prompt) -> str:
        return self.generate_response(full_prompt)  # Generate response using the prompt

    # Main loop to run the agent
    def run(self, user_input: str, memory=None, max_iterations: int = 10) -> Memory:
        memory = memory or Memory()  # Initialize memory if not provided
        self.set_current_task(memory, user_input)  # Set the initial task

        for _ in range(max_iterations):  # Iterate up to the maximum number of iterations
            prompt = self.construct_prompt(self.goals, memory, self.actions)  # Construct the prompt
            response = self.prompt_llm_for_action(prompt)  # Get the response from the language model
            action, invocation = self.get_action(response)  # Determine the action to take
            result = self.environment.execute_action(action, invocation["args"])  # Execute the action
            self.update_memory(memory, response, result)  # Update the memory with the results
            if self.should_terminate(response):  # Check if the agent should terminate
                break

        return memory  # Return the updated memory
