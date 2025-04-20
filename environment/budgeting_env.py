"""
Script Name: budgeting_env.py
Author: Vasu Chukka
Created: 2025-04-19
Last Modified: 2025-04-19
Description: Executes budgeting tools in a controlled environment,
             formats results, and handles errors or exceptions.
"""

import time
import traceback
from typing import Any, Dict
from tools.shared_registry import Action

class BudgetingEnvironment:
    """
    Environment class that executes tools/actions for the BudgetingAgent.

    Responsibilities:
    - Execute actions passed by the agent
    - Wrap results with metadata
    - Catch and log execution errors
    """

    def execute_action(self, action: Action, args: Dict) -> Dict:
        """
        Executes the action safely and returns formatted result.

        Args:
            action: The Action object to be executed
            args: Parameters for the action function

        Returns:
            Dictionary with execution status, result, and timestamp
        """
        try:
            result = action.execute(**args)
            return self.format_result(result)
        except Exception as e:
            return {
                "tool_executed": False,
                "error": str(e),
                "traceback": traceback.format_exc()
            }

    def format_result(self, result: Any) -> Dict:
        """
        Wraps the result with metadata for memory logging.

        Args:
            result: Raw result from action function

        Returns:
            Structured dictionary with result and timestamp
        """
        return {
            "tool_executed": True,
            "result": result,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")
        }
