"""
Script Name: budgeting_agent.py
Author: Vasu Chukka
Created: 2025-04-19
Last Modified: 2025-04-19
Description: Implements a budgeting AI agent with custom language processing and tool integration.
"""

import tools.budgeting_tools
from tools.shared_registry import tools
from agents.base import BaseAgent, Goal
from tools.shared_registry import PythonActionRegistry
from environment.budgeting_env import BudgetingEnvironment
from goals.budgeting_goals import get_budgeting_goals
from agents.base import AgentLanguage
from openai import OpenAI
from dataclasses import dataclass
from typing import List, Dict
from dotenv import load_dotenv
import json
import os

# Load environment variables from .env file
load_dotenv()
# Set OpenAI API key from environment variable
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


@dataclass
class Prompt:
    """
    Represents the structure of a prompt to be sent to the AI model.
    Contains messages, tools, and optional metadata.
    """
    messages: List[Dict]
    tools: List[Dict]
    metadata: dict = None


class BudgetingLanguage(AgentLanguage):
    """
    Custom language class for the budgeting agent.
    Handles prompt construction and response parsing.
    """

    def construct_prompt(self, actions, environment, goals, memory):
        """
        Constructs a prompt for the AI model based on actions, environment, goals, and memory.

        Args:
            actions: List of available actions for the agent.
            environment: The environment in which the agent operates.
            goals: The goals the agent is trying to achieve.
            memory: The memory object containing past interactions.

        Returns:
            A Prompt object containing the constructed messages and tools.
        """
        prompt = []

        goal_descriptions = "\n".join([f"{g.name}: {g.description}" for g in goals])
        agent_rules = (
                "When updating a transaction, assume the most recent match is correct unless otherwise specified. "
                "Do not prompt the user for more details unless multiple very similar matches are found. "
                "Use available tools to complete the task whenever possible."
        )
        # Add system-level information about goals
        prompt.append({
            "role": "system",
            "content": f"{goal_descriptions}\n\n{agent_rules}"
        })

        # Add memory entries to the prompt
        # Convert memory entries to OpenAI-compatible messages
        valid_roles = ["user", "assistant", "system"]

        prompt += [
            {
                "role": mem["type"] if mem["type"] in valid_roles else "assistant",
                "content": mem["content"]
            }
            for mem in memory.get_memories()
            if "type" in mem and "content" in mem
        ]

        # Prepare tools information for the prompt
        tools = [{
            "type": "function",
            "function": {
                "name": a.name,
                "description": a.description,
                "parameters": a.parameters,
            }
        } for a in actions]

        return Prompt(messages=prompt, tools=tools)

    def parse_response(self, response: str) -> dict:
        """
        Parses the response from the AI model.

        Args:
            response: The raw response string from the AI model.

        Returns:
            A dictionary containing the parsed response.
        """
        try:
            # Attempt to parse the response as JSON
            return json.loads(response)
        except Exception:
            # If parsing fails, return a terminate tool with the raw response
            return {
                "tool": "terminate",
                "args": {"message": response}
            }


def generate_response(prompt: Prompt) -> str:
    """
    Generates a response from the AI model based on the given prompt.

    Args:
        prompt: The Prompt object containing messages and tools.

    Returns:
        A string representing the AI model's response.
    """
    response = client.chat.completions.create(
        model="gpt-4o",  # Specify the model to use
        messages=prompt.messages,  # Provide the messages for the prompt
        tools=prompt.tools,  # Include the tools in the prompt
        max_tokens=1024,  # Set the maximum number of tokens for the response
        tool_choice="auto"
    )

    # Check if the response includes tool calls
    if response.choices[0].message.tool_calls:
        tool = response.choices[0].message.tool_calls[0]
        # Return the tool name and arguments as JSON
        return json.dumps({
            "tool": tool.function.name,
            "args": json.loads(tool.function.arguments)
        })
    else:
        # Return the plain content of the response
        return response.choices[0].message.content


def create_budgeting_agent():
    """
    Creates and initializes a budgeting agent.

    Returns:
        An instance of BaseAgent configured for budgeting tasks.
    """
    print("🧰 Registered tools:", list(tools.keys()))

    # Create and return the budgeting agent
    return BaseAgent(
        goals=get_budgeting_goals(),  # Retrieve the goals for budgeting
        agent_language=BudgetingLanguage(),  # Use the custom language class
        action_registry=PythonActionRegistry(tags=["budgeting"]),  # Register actions with the "budgeting" tag
        generate_response=generate_response,  # Set the response generation function
        environment=BudgetingEnvironment()  # Initialize the budgeting environment
    )
