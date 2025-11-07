"""
Aegis Control Loop - Core orchestration with replay support.

The control loop coordinates observation, intent generation, policy checks,
action execution, and logging. In replay mode, it reconstructs past executions
without performing any real actions.
"""

import time
from typing import Optional, Dict, Any, List
from datetime import datetime

from aegis_logging.logger import AegisLogger
from aegis_logging.session import SessionManager, AegisSession
from aegis_logging.log_inspector import LogInspector


class ControlLoop:
    """
    Main Aegis control loop with cycle management and replay capability.

    In normal mode: Observes -> Generates Intent -> Checks Policy -> Executes Action
    In replay mode: Reconstructs past execution from logs without side effects
    """

    def __init__(
        self,
        logger: Optional[AegisLogger] = None,
        max_cycles: int = 100,
        cycle_delay_seconds: float = 1.0
    ):
        """
        Initialize control loop.

        Args:
            logger: AegisLogger instance (creates default if None)
            max_cycles: Maximum cycles per session
            cycle_delay_seconds: Delay between cycles
        """
        self.logger = logger or AegisLogger()
        self.max_cycles = max_cycles
        self.cycle_delay_seconds = cycle_delay_seconds
        self.session: Optional[AegisSession] = None

    def run(self, session: Optional[AegisSession] = None):
        """
        Run the control loop in normal mode.

        Args:
            session: Optional existing session (creates new if None)
        """
        if session is None:
            session = SessionManager.create_session(replay_mode=False)
        else:
            SessionManager._current_session = session

        self.session = session

        print(f"Starting Aegis Control Loop")
        print(f"Session ID: {session.session_id}")
        print(f"Max Cycles: {self.max_cycles}")
        print()

        try:
            for cycle_num in range(1, self.max_cycles + 1):
                cycle_id = session.start_cycle()
                print(f" Cycle {cycle_id}/{self.max_cycles}")

                self._execute_cycle(cycle_id)

                if cycle_num < self.max_cycles:
                    time.sleep(self.cycle_delay_seconds)

        except KeyboardInterrupt:
            print("\n⏸  Control loop interrupted by user")
        except Exception as e:
            print(f"\n Control loop error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            session.end()
            SessionManager.end_session()
            print(f"\n Session complete: {session.cycle_count} cycles, {session.total_actions} actions")

    def _execute_cycle(self, cycle_id: int):
        """Execute a single cycle of the control loop."""
        start_time = time.time()

        # Step 1: Observe
        observation = self._observe()
        print(f"    Observed: {observation['summary']}")

        # Step 2: Generate intent
        intent = self._generate_intent(observation)
        print(f"   Intent: {intent}")

        # Step 3: Policy check
        policy_decision = self._check_policy(intent)
        print(f"    Policy: {policy_decision}")

        # Step 4: Execute action (if allowed)
        if policy_decision == "ALLOW":
            action, result, error = self._execute_action(intent)
        else:
            action = "BLOCKED"
            result = "blocked_by_policy"
            error = None

        duration_ms = int((time.time() - start_time) * 1000)

        # Log the event
        self.logger.log_event(
            intent=intent,
            action=action,
            policy_decision=policy_decision,
            result=result,
            cycle_id=cycle_id,
            duration_ms=duration_ms,
            error=error,
            metadata={'observation': observation}
        )

        print(f"   Result: {result} ({duration_ms}ms)")

    def _observe(self) -> Dict[str, Any]:
        """Observe current system state (stub for Day 5)."""
        return {
            'summary': 'System idle',
            'active_windows': 0,
            'cpu_usage': 15.2
        }

    def _generate_intent(self, observation: Dict[str, Any]) -> str:
        """Generate intent based on observation (stub for Day 5)."""
        return "maintain_idle_state"

    def _check_policy(self, intent: str) -> str:
        """Check if intent is allowed by policy (stub for Day 5)."""
        # Simple allowlist for demo
        if intent in ["maintain_idle_state", "monitor_system"]:
            return "ALLOW"
        return "DENY"

    def _execute_action(self, intent: str) -> tuple[str, str, Optional[str]]:
        """
        Execute action based on intent (stub for Day 5).

        Returns:
            Tuple of (action_name, result, error_message)
        """
        # Stub implementation
        time.sleep(0.1)  # Simulate work
        return ("no_action", "success", None)

    def replay(self, session_id: str):
        """
        Replay a past session from logs (DRY RUN ONLY).

        Args:
            session_id: UUID of session to replay

        Raises:
            ValueError: If session not found
        """
        print(f" REPLAY MODE - Session {session_id}")
        print("  DRY RUN: No actions will be executed\n")

        inspector = LogInspector(db_path=str(self.logger.db_path))

        try:
            replay_data = inspector.get_replay_data(session_id)
        except ValueError as e:
            print(f" {e}")
            return

        events = replay_data['events']

        print(f" Session: {session_id}")
        print(f" Events: {replay_data['event_count']}")
        print(f" Cycles: {replay_data['max_cycle']}")
        print(f" Started: {replay_data['started_at']}")
        print(f" Ended: {replay_data['ended_at']}")
        print(f"\n{'='*80}\n")

        current_cycle = None

        for event in events:
            if event['cycle_id'] != current_cycle:
                current_cycle = event['cycle_id']
                print(f"\n Cycle {current_cycle}")
                print(f"{''*80}")

            self._display_event(event)

            # Small delay for readability
            time.sleep(0.1)

        print(f"\n{'='*80}")
        print(f" Replay complete: {len(events)} events replayed")

        # Summary stats
        error_count = sum(1 for e in events if e['error'])
        success_count = sum(1 for e in events if e['result'] == 'success')
        print(f"\n Summary:")
        print(f"   Success: {success_count}")
        print(f"   Errors: {error_count}")
        print(f"   Total: {len(events)}")

    def _display_event(self, event: Dict[str, Any]):
        """Display a single event during replay."""
        timestamp = event['timestamp'][:19]  # Trim to datetime
        intent = event['intent']
        action = event['action']
        policy = event['policy_decision']
        result = event['result']
        duration = event['duration_ms']
        error = event.get('error')

        result_icon = "" if result == "success" else "" if error else ""

        print(f"  {timestamp} | {result_icon} {intent}")
        print(f"    Action: {action} | Policy: {policy} | Duration: {duration}ms")

        if error:
            print(f"     Error: {error}")

        metadata = event.get('metadata')
        if metadata:
            try:
                import json
                meta_dict = json.loads(metadata)
                print(f"     Metadata: {json.dumps(meta_dict, indent=6)}")
            except:
                pass
