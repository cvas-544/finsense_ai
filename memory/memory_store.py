"""
Script Name: memory_store.py
Author: Vasu Chukka
Created: 2025-04-19
Last Modified: 2025-04-19
Description: Implements the Memory class for agents, storing conversation history
             and intermediate results in a structured format.
"""

class Memory:
    """
    A simple memory system for storing and retrieving interactions.
    Each memory entry is a dictionary with a 'type' and 'content'.
    """

    def __init__(self):
        self.memories = []

    def add_memory(self, memory_entry: dict):
        """
        Adds a new memory entry.

        Args:
            memory_entry: A dictionary with at least 'type' and 'content' keys
        """
        if "type" in memory_entry and "content" in memory_entry:
            self.memories.append(memory_entry)

    def get_memories(self):
        """
        Returns all memory entries in chronological order.
        """
        return self.memories

    def clear(self):
        """
        Clears all stored memories.
        """
        self.memories = []
