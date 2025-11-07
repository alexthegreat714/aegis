"""
Policy enforcement engine.

Loads and enforces policy rules from policy.yaml.
"""

from typing import Dict, Any, List, Optional
from pathlib import Path
import yaml

from intents.intent_schema import Intent
from aegis_logging.logger import AegisLogger


class PolicyDecision:
    """Result of a policy check."""

    def __init__(self, allowed: bool, reason: str, requires_approval: bool = False):
        """
        Initialize policy decision.

        Args:
            allowed: Whether action is allowed
            reason: Explanation for decision
            requires_approval: Whether human approval is required
        """
        self.allowed = allowed
        self.reason = reason
        self.requires_approval = requires_approval

    def __repr__(self) -> str:
        if self.requires_approval:
            return f"PolicyDecision(APPROVAL_REQUIRED: {self.reason})"
        return f"PolicyDecision({'ALLOW' if self.allowed else 'BLOCK'}: {self.reason})"


class PolicyEngine:
    """
    Loads and enforces policy rules.

    Validates intents against policy configuration.
    """

    def __init__(self, policy_path: str, logger: AegisLogger):
        """
        Initialize policy engine.

        Args:
            policy_path: Path to policy.yaml file
            logger: Logging system
        """
        self.policy_path = Path(policy_path)
        self.logger = logger
        self.policy: Dict[str, Any] = {}
        self.load_policy()

    def load_policy(self) -> None:
        """Load policy from YAML file."""
        try:
            with open(self.policy_path, 'r') as f:
                self.policy = yaml.safe_load(f)

            self.logger.log_event(
                event_type="policy_loaded",
                data={"policy_path": str(self.policy_path), "mode": self.policy.get("mode")},
                status="success"
            )
            print(f"[Policy] Loaded policy from {self.policy_path}")
            print(f"[Policy] Mode: {self.policy.get('mode', 'unknown')}")

        except Exception as e:
            self.logger.log_event(
                event_type="policy_load_failed",
                data={"error": str(e)},
                status="error"
            )
            raise RuntimeError(f"Failed to load policy: {e}")

    def reload_policy(self) -> None:
        """Reload policy from disk (for runtime updates)."""
        self.load_policy()

    def check_intent(self, intent: Intent) -> PolicyDecision:
        """
        Check if an intent is allowed by policy.

        Args:
            intent: The intent to validate

        Returns:
            PolicyDecision indicating if action is allowed
        """
        # Get operation mode
        mode = self.policy.get("mode", "assist")

        # Step 1: Check if action type is in sandbox-only list
        if self.is_sandbox_only(intent.action_type.value):
            # Check if action is targeting sandbox directory
            target_path = intent.parameters.get("path") or intent.parameters.get("target")
            if target_path:
                sandbox_dir = Path("sandbox").resolve()
                try:
                    target_resolved = Path(target_path).resolve()
                    if not target_resolved.is_relative_to(sandbox_dir):
                        return PolicyDecision(
                            allowed=False,
                            reason=f"Action '{intent.action_type.value}' can only be performed in sandbox directory"
                        )
                except (ValueError, OSError):
                    return PolicyDecision(
                        allowed=False,
                        reason=f"Invalid path for sandbox-only action: {target_path}"
                    )

        # Step 2: Check path restrictions (for file/directory operations)
        if intent.category in ["filesystem", "vscode"]:
            target_path = intent.parameters.get("path") or intent.parameters.get("target") or intent.parameters.get("file_path")
            if target_path and not self.is_path_allowed(target_path):
                return PolicyDecision(
                    allowed=False,
                    reason=f"Path '{target_path}' is restricted by policy"
                )

        # Step 3: In assist mode, all actions require approval
        if mode == "assist":
            return PolicyDecision(
                allowed=False,
                reason=f"Running in assist mode - action '{intent.action_type.value}' requires approval",
                requires_approval=True
            )

        # Step 4: Check action permissions
        decision = self._check_action_permission(intent)

        # Log policy decision
        self.logger.log_event(
            event_type="policy_check",
            data={
                "intent": intent.to_dict(),
                "decision": str(decision)
            },
            status="info"
        )

        return decision

    def _check_action_permission(self, intent: Intent) -> PolicyDecision:
        """
        Check specific action permission.

        Args:
            intent: Intent to check

        Returns:
            PolicyDecision
        """
        action_type = intent.action_type.value
        category = intent.category

        # Get actions config
        actions = self.policy.get("actions", {})
        category_actions = actions.get(category, {})

        # Get permission for this action (default to block if not specified)
        permission = category_actions.get(action_type, "block")

        # Additional checks for meta actions (always allowed)
        if category == "meta":
            return PolicyDecision(allowed=True, reason=f"Meta action '{action_type}' is always allowed")

        if permission == "allow":
            return PolicyDecision(allowed=True, reason=f"Action '{action_type}' is allowed by policy")
        elif permission == "require_approval":
            return PolicyDecision(
                allowed=False,
                reason=f"Action '{action_type}' requires human approval",
                requires_approval=True
            )
        else:  # block
            return PolicyDecision(allowed=False, reason=f"Action '{action_type}' is blocked by policy")

    def is_path_allowed(self, path: str) -> bool:
        """
        Check if a file path is allowed.

        Args:
            path: File path to check

        Returns:
            True if path is allowed
        """
        restricted = self.policy.get("restricted_paths", [])
        allowed = self.policy.get("allowed_paths", [])

        try:
            path_obj = Path(path).resolve()
        except (ValueError, OSError) as e:
            self.logger.log_event(
                event_type="path_validation_error",
                data={"path": path, "error": str(e)},
                status="warning"
            )
            return False

        # Always allow sandbox directory
        try:
            sandbox_dir = Path("sandbox").resolve()
            if path_obj.is_relative_to(sandbox_dir):
                return True
        except (ValueError, OSError):
            pass

        # Check restricted paths - these are NEVER allowed
        for restricted_path in restricted:
            try:
                restricted_resolved = Path(restricted_path).resolve()
                if path_obj.is_relative_to(restricted_resolved):
                    self.logger.log_event(
                        event_type="path_blocked",
                        data={"path": path, "reason": f"In restricted path: {restricted_path}"},
                        status="warning"
                    )
                    return False
            except (ValueError, OSError):
                continue

        # If allowed_paths is defined, path must be in one of them
        if allowed:
            for allowed_path in allowed:
                try:
                    allowed_resolved = Path(allowed_path).resolve()
                    if path_obj.is_relative_to(allowed_resolved):
                        return True
                except (ValueError, OSError):
                    continue
            # Path not in any allowed path
            self.logger.log_event(
                event_type="path_blocked",
                data={"path": path, "reason": "Not in allowed_paths list"},
                status="warning"
            )
            return False

        # No restrictions - allow by default
        return True

    def is_sandbox_only(self, action_type: str) -> bool:
        """
        Check if action is sandbox-only.

        Args:
            action_type: Action type to check

        Returns:
            True if action can only run in sandbox
        """
        sandbox_only = self.policy.get("sandbox_only", [])
        return action_type in sandbox_only

    def get_mode(self) -> str:
        """
        Get current operation mode.

        Returns:
            Current mode (assist | execute | autonomous)
        """
        return self.policy.get("mode", "assist")
