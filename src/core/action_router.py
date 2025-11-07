"""
Action router for policy-aware intent execution.

Routes intents through sandbox, policy engine, and approval workflows.
"""

from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime

from aegis_logging.logger import AegisLogger
from core.policy_engine import PolicyEngine
from core.sandbox_revision import SandboxRevisionManager
from core.interactive import InteractivePause


class ActionRouter:
    """
    Routes intents through the proper execution pipeline.

    Flow:
    1. Intent arrives (from DeepCoder reasoning)
    2. Policy check (allow/block/require_approval)
    3. Sandbox check (file modifications → sandbox)
    4. Interactive pause (if required by policy or risk level)
    5. Execution or delegation to Claude
    """

    def __init__(
        self,
        logger: AegisLogger,
        policy_engine: PolicyEngine,
        sandbox_manager: SandboxRevisionManager,
        interactive_pause: InteractivePause,
        settings: Dict[str, Any]
    ):
        """
        Initialize action router.

        Args:
            logger: Logging system
            policy_engine: Policy enforcement
            sandbox_manager: Sandbox revision system
            interactive_pause: Interactive pause system
            settings: System settings
        """
        self.logger = logger
        self.policy_engine = policy_engine
        self.sandbox_manager = sandbox_manager
        self.interactive_pause = interactive_pause
        self.settings = settings

    def route_intent(self, intent: Dict[str, Any]) -> Dict[str, Any]:
        """
        Route intent through the execution pipeline.

        Args:
            intent: Intent packet from reasoning

        Returns:
            Routing result dictionary
        """
        intent_id = intent.get("intent_id", "unknown")
        intent_type = intent.get("intent_type", "unknown")
        risk_level = intent.get("risk_level", "medium")

        self.logger.log_event(
            event_type="intent_routing_start",
            data={
                "intent_id": intent_id,
                "intent_type": intent_type,
                "risk_level": risk_level
            },
            status="info"
        )

        # Step 1: Policy check
        policy_result = self._check_policy(intent)

        if not policy_result["allowed"]:
            return {
                "status": "blocked",
                "reason": policy_result["reason"],
                "intent_id": intent_id
            }

        # Step 2: Sandbox check
        sandbox_required = self._requires_sandbox(intent)

        if sandbox_required:
            return self._route_to_sandbox(intent)

        # Step 3: Interactive pause check
        pause_required = (
            policy_result.get("requires_approval", False) or
            risk_level in ["high", "critical"] or
            intent.get("requires_approval", False)
        )

        if pause_required:
            pause_result = self._interactive_pause_for_intent(intent)

            if pause_result["command"] == "abort":
                return {
                    "status": "aborted",
                    "reason": "User aborted during pause window",
                    "intent_id": intent_id
                }
            elif pause_result["command"] == "skip":
                return {
                    "status": "skipped",
                    "reason": "User skipped during pause window",
                    "intent_id": intent_id
                }

        # Step 4: Route based on intent type
        if intent_type == "query":
            return self._execute_query(intent)
        elif intent_type == "modify_file":
            return self._route_to_sandbox(intent)
        elif intent_type == "execute_command":
            return self._execute_command(intent)
        elif intent_type == "delegate_to_claude":
            return self._delegate_to_claude(intent)
        else:
            return {
                "status": "error",
                "reason": f"Unknown intent type: {intent_type}",
                "intent_id": intent_id
            }

    def _check_policy(self, intent: Dict[str, Any]) -> Dict[str, bool]:
        """
        Check intent against policy engine.

        Args:
            intent: Intent packet

        Returns:
            Policy decision
        """
        intent_type = intent.get("intent_type", "unknown")
        risk_level = intent.get("risk_level", "medium")

        # Create pseudo-intent for policy check
        # TODO: Use actual Intent object from intent_schema
        decision = {
            "allowed": True,
            "requires_approval": False,
            "reason": "Policy check passed"
        }

        # High-risk intents always require approval
        if risk_level in ["high", "critical"]:
            decision["requires_approval"] = True
            decision["reason"] = f"High risk level: {risk_level}"

        # File modifications require approval in assist mode
        if intent_type == "modify_file":
            mode = self.policy_engine.get_mode()
            if mode == "assist":
                decision["requires_approval"] = True
                decision["reason"] = "File modification requires approval in assist mode"

        return decision

    def _requires_sandbox(self, intent: Dict[str, Any]) -> bool:
        """
        Check if intent requires sandbox isolation.

        Args:
            intent: Intent packet

        Returns:
            True if sandbox required
        """
        intent_type = intent.get("intent_type", "unknown")

        # All file modifications MUST go through sandbox
        if intent_type == "modify_file":
            return True

        if intent.get("requires_sandbox", False):
            return True

        # Check if actions involve file operations
        actions = intent.get("actions", [])
        for action in actions:
            action_type = action.get("type", "")
            if action_type in ["write", "delete", "modify", "create"]:
                return True

        return False

    def _route_to_sandbox(self, intent: Dict[str, Any]) -> Dict[str, Any]:
        """
        Route intent to sandbox for safe execution.

        Args:
            intent: Intent packet

        Returns:
            Routing result
        """
        intent_id = intent.get("intent_id", "unknown")
        task = intent.get("task", "Unknown task")
        reasoning_summary = intent.get("reasoning_summary", "")
        risk_level = intent.get("risk_level", "medium")
        actions = intent.get("actions", [])

        # Extract file modifications
        files_to_modify = []
        for action in actions:
            if action.get("type") in ["write", "modify", "create"]:
                files_to_modify.append({
                    "path": action.get("target", ""),
                    "action": action.get("type"),
                    "content": action.get("content", "")
                })

        if not files_to_modify:
            return {
                "status": "error",
                "reason": "No file modifications found in intent",
                "intent_id": intent_id
            }

        # Create revision bundle
        try:
            bundle = self.sandbox_manager.create_revision_bundle(
                task_description=task,
                reasoning=reasoning_summary,
                risk_level=risk_level,
                files_to_modify=files_to_modify,
                task_slug=intent_id[:20]
            )

            return {
                "status": "sandboxed",
                "revision_id": bundle.revision_id,
                "intent_id": intent_id,
                "message": "Intent routed to sandbox - awaiting approval"
            }

        except Exception as e:
            self.logger.log_event(
                event_type="sandbox_routing_failed",
                data={"intent_id": intent_id, "error": str(e)},
                status="error"
            )

            return {
                "status": "error",
                "reason": f"Sandbox routing failed: {e}",
                "intent_id": intent_id
            }

    def _interactive_pause_for_intent(self, intent: Dict[str, Any]) -> Dict[str, str]:
        """
        Trigger interactive pause for intent approval.

        Args:
            intent: Intent packet

        Returns:
            Pause result
        """
        reasoning_summary = intent.get("reasoning_summary", "No summary available")
        risk_level = intent.get("risk_level", "medium")

        command = self.interactive_pause.pause_for_reasoning(
            reasoning_text=reasoning_summary,
            risk_level=risk_level
        )

        return {"command": command}

    def _execute_query(self, intent: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute query intent (read-only).

        Args:
            intent: Intent packet

        Returns:
            Execution result
        """
        # Query intents are safe - just return success
        return {
            "status": "completed",
            "intent_id": intent.get("intent_id"),
            "result": "Query intent completed"
        }

    def _execute_command(self, intent: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute command intent (placeholder).

        Args:
            intent: Intent packet

        Returns:
            Execution result
        """
        # TODO: Implement command execution with policy checks
        return {
            "status": "not_implemented",
            "intent_id": intent.get("intent_id"),
            "message": "Command execution not implemented yet"
        }

    def _delegate_to_claude(self, intent: Dict[str, Any]) -> Dict[str, Any]:
        """
        Delegate intent to Claude for execution.

        This is where intent packets are formatted and sent to Claude.

        Args:
            intent: Intent packet

        Returns:
            Delegation result
        """
        intent_id = intent.get("intent_id", "unknown")

        # Format intent as YAML for Claude
        intent_yaml = self._format_intent_for_claude(intent)

        self.logger.log_event(
            event_type="intent_delegated_to_claude",
            data={
                "intent_id": intent_id,
                "intent_yaml_length": len(intent_yaml)
            },
            status="info"
        )

        return {
            "status": "delegated",
            "intent_id": intent_id,
            "claude_message": intent_yaml,
            "message": "Intent delegated to Claude for execution"
        }

    def _format_intent_for_claude(self, intent: Dict[str, Any]) -> str:
        """
        Format intent packet as YAML for Claude.

        Args:
            intent: Intent dictionary

        Returns:
            YAML string (what Claude sees - NO verbose reasoning)
        """
        import yaml

        # Remove internal fields that Claude shouldn't see
        claude_intent = {
            "intent_id": intent.get("intent_id"),
            "intent_type": intent.get("intent_type"),
            "task": intent.get("task"),
            "actions": intent.get("actions", []),
            "test_plan": intent.get("test_plan", []),
            "rollback_plan": intent.get("rollback_plan"),
            "reasoning_summary": intent.get("reasoning_summary")  # Brief summary only
        }

        return yaml.dump(claude_intent, default_flow_style=False, sort_keys=False)
