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
        # TODO: Implement full policy checking logic

        # Get operation mode
        mode = self.policy.get("mode", "assist")

        # In assist mode, all actions require approval
        if mode == "assist":
            return PolicyDecision(
                allowed=False,
                reason=f"Running in assist mode - action '{intent.action_type}' requires approval",
                requires_approval=True
            )

        # Check action permissions
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
        # TODO: Implement granular permission checking
        # - Check action category (desktop, vscode, filesystem, system)
        # - Check specific action type
        # - Check path restrictions
        # - Check sandbox-only actions

        action_type = intent.action_type.value
        category = intent.category

        # Get actions config
        actions = self.policy.get("actions", {})
        category_actions = actions.get(category, {})

        # Get permission for this action
        permission = category_actions.get(action_type, "block")

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
        # TODO: Implement path validation
        # - Check against restricted_paths
        # - Check against allowed_paths
        # - Check if in sandbox

        restricted = self.policy.get("restricted_paths", [])
        allowed = self.policy.get("allowed_paths", [])

        path_obj = Path(path).resolve()

        # Check restricted paths
        for restricted_path in restricted:
            if path_obj.is_relative_to(Path(restricted_path)):
                return False

        # If allowed_paths is defined, path must be in one of them
        if allowed:
            for allowed_path in allowed:
                if path_obj.is_relative_to(Path(allowed_path)):
                    return True
            return False

        # No restrictions
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
