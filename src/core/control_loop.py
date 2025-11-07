"""
Aegis Control Loop - Core orchestration with replay, heartbeat, and hot-reload.

The control loop coordinates observation, intent generation, policy checks,
action execution, and logging. Supports multiple modes: normal, sandbox, assist, replay.
"""

import time
from typing import Optional, Dict, Any
from datetime import datetime

from aegis_logging.logger import AegisLogger
from aegis_logging.session import SessionManager, AegisSession
from aegis_logging.log_inspector import LogInspector
from utils.config_loader import ConfigLoader
from utils.health_monitor import HealthMonitor


class ControlLoop:
    """
    Main Aegis control loop with cycle management and multiple modes.

    Modes:
    - Normal: Standard operation
    - Sandbox: Mock actions, dry-run testing
    - Assist: Interactive mode with confirmations
    - Replay: Reconstruct past execution from logs (read-only)
    """

    def __init__(
        self,
        logger: Optional[AegisLogger] = None,
        config: Optional[ConfigLoader] = None,
        mode: str = "normal"
    ):
        """
        Initialize control loop.

        Args:
            logger: AegisLogger instance (creates default if None)
            config: ConfigLoader instance (creates default if None)
            mode: Operation mode (normal, sandbox, assist, replay)
        """
        self.config = config or ConfigLoader()
        self.logger = logger or AegisLogger(
            db_path=self.config.get('logging.db_path', 'data/aegis.db'),
            enable_jsonl=self.config.get('logging.enable_jsonl', True)
        )
        self.mode = mode
        self.session: Optional[AegisSession] = None
        self.health_monitor = HealthMonitor()

        # Load config values
        self.max_cycles = self.config.get('control_loop.max_cycles', 100)
        self.cycle_delay_seconds = self.config.get('control_loop.cycle_delay_seconds', 1.0)
        self.enable_heartbeat = self.config.get('control_loop.enable_heartbeat', True)
        self.heartbeat_interval = self.config.get('control_loop.heartbeat_interval_cycles', 5)

    def run(self, session: Optional[AegisSession] = None, cycles: Optional[int] = None):
        """
        Run the control loop in normal/sandbox/assist mode.

        Args:
            session: Optional existing session (creates new if None)
            cycles: Override max_cycles if provided
        """
        if session is None:
            session = SessionManager.create_session(replay_mode=False)
        else:
            SessionManager._current_session = session

        self.session = session
        max_cycles = cycles if cycles is not None else self.max_cycles

        # Mode-specific startup
        if self.mode == "sandbox":
            print("SANDBOX MODE - Mock actions, dry-run only")
        elif self.mode == "assist":
            print("ASSIST MODE - Interactive with confirmations")

        print(f"Starting Aegis Control Loop")
        print(f"Session ID: {session.session_id}")
        print(f"Max Cycles: {max_cycles}")
        print(f"Mode: {self.mode}")
        print()

        try:
            for cycle_num in range(1, max_cycles + 1):
                cycle_id = session.start_cycle()
                print(f" Cycle {cycle_id}/{max_cycles}")

                # Check for config changes
                if self.config.check_and_reload():
                    print("  [Config reloaded]")
                    self._update_from_config()

                # Execute cycle
                self._execute_cycle(cycle_id)

                # Heartbeat logging
                if self.enable_heartbeat and cycle_id % self.heartbeat_interval == 0:
                    self._log_heartbeat(cycle_id)

                # Prune old heartbeats
                if cycle_id % 50 == 0:
                    max_hb = self.config.get('logging.max_heartbeat_entries', 1000)
                    deleted = self.logger.prune_heartbeats(max_hb)
                    if deleted > 0:
                        print(f"  [Pruned {deleted} old heartbeat entries]")

                if cycle_num < max_cycles:
                    time.sleep(self.cycle_delay_seconds)

        except KeyboardInterrupt:
            print("\n Control loop interrupted by user")
        except Exception as e:
            print(f"\n Control loop error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            session.end()
            SessionManager.end_session()
            print(f"\n Session complete: {session.cycle_count} cycles, {session.total_actions} actions")

    def _update_from_config(self):
        """Update settings from reloaded config."""
        self.max_cycles = self.config.get('control_loop.max_cycles', 100)
        self.cycle_delay_seconds = self.config.get('control_loop.cycle_delay_seconds', 1.0)
        self.enable_heartbeat = self.config.get('control_loop.enable_heartbeat', True)
        self.heartbeat_interval = self.config.get('control_loop.heartbeat_interval_cycles', 5)

    def _log_heartbeat(self, cycle_id: int):
        """Log heartbeat with health metrics."""
        health_config = self.config.get_section('health')

        snapshot = self.health_monitor.get_health_snapshot(
            include_cpu=health_config.get('monitor_cpu', True),
            include_memory=health_config.get('monitor_memory', True),
            include_window=health_config.get('monitor_active_window', True)
        )

        self.logger.log_heartbeat(
            cycle_id=cycle_id,
            cpu_percent=snapshot.get('cpu_percent'),
            memory_percent=snapshot.get('memory_percent'),
            active_window=snapshot.get('active_window')
        )

        print(f"  [Heartbeat: CPU={snapshot.get('cpu_percent', 0):.1f}% RAM={snapshot.get('memory_percent', 0):.1f}%]")

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

        # Step 4: Execute action (if allowed and not sandbox)
        if policy_decision == "ALLOW":
            if self.mode == "sandbox":
                action, result, error = "mock_action", "success", None
                print(f"    [Sandbox: skipped actual execution]")
            elif self.mode == "assist":
                if self._confirm_action(intent):
                    action, result, error = self._execute_action(intent)
                else:
                    action, result, error = "user_declined", "skipped", None
            else:
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
            metadata={'observation': observation, 'mode': self.mode}
        )

        print(f"   Result: {result} ({duration_ms}ms)")

    def _confirm_action(self, intent: str) -> bool:
        """Ask user to confirm action in assist mode."""
        response = input(f"  Execute '{intent}'? [y/N]: ").strip().lower()
        return response == 'y'

    def _observe(self) -> Dict[str, Any]:
        """Observe current system state (stub for Day 6)."""
        return {
            'summary': 'System idle',
            'active_windows': 0,
            'cpu_usage': 15.2
        }

    def _generate_intent(self, observation: Dict[str, Any]) -> str:
        """Generate intent based on observation (stub for Day 6)."""
        return "maintain_idle_state"

    def _check_policy(self, intent: str) -> str:
        """Check if intent is allowed by policy."""
        policy_mode = self.config.get('policy.mode', 'permissive')
        allowed_intents = self.config.get('policy.allowed_intents', [])

        if policy_mode == "permissive":
            return "ALLOW"
        elif policy_mode == "strict":
            return "ALLOW" if intent in allowed_intents else "DENY"
        elif policy_mode == "learning":
            # In learning mode, allow but log
            return "ALLOW"
        else:
            return "DENY"

    def _execute_action(self, intent: str) -> tuple[str, str, Optional[str]]:
        """
        Execute action based on intent (stub for Day 6).

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
                print(f"{'─'*80}")

            self._display_event(event)

            # Small delay for readability
            time.sleep(0.1)

        print(f"\n{'='*80}")
        print(f" Replay complete: {len(events)} events replayed")

        # Summary stats
        error_count = sum(1 for e in events if e['error'])
        success_count = sum(1 for e in events if e['result'] == 'success')
        heartbeat_count = sum(1 for e in events if e['intent'] == 'heartbeat')

        print(f"\n Summary:")
        print(f"   Success: {success_count}")
        print(f"   Errors: {error_count}")
        print(f"   Heartbeats: {heartbeat_count}")
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

        # Special display for heartbeats
        if intent == "heartbeat":
            try:
                import json
                meta = json.loads(event.get('metadata', '{}'))
                cpu = meta.get('cpu_percent', 0)
                ram = meta.get('memory_percent', 0)
                print(f"  {timestamp} | [Heartbeat] CPU={cpu:.1f}% RAM={ram:.1f}%")
            except:
                print(f"  {timestamp} | [Heartbeat]")
            return

        result_icon = "" if result == "success" else " " if error else " "

        print(f"  {timestamp} | {result_icon} {intent}")
        print(f"    Action: {action} | Policy: {policy} | Duration: {duration}ms")

        if error:
            print(f"     Error: {error}")

    def test_connection(self) -> bool:
        """
        Test database connection and config loading.

        Returns:
            True if all systems operational
        """
        print("Testing Aegis subsystems...")

        # Test config
        try:
            config_dict = self.config.to_dict()
            print(f"  Config: OK ({len(config_dict)} sections)")
        except Exception as e:
            print(f"  Config: FAILED - {e}")
            return False

        # Test database
        try:
            with self.logger._get_connection() as conn:
                cursor = conn.execute("SELECT COUNT(*) FROM aegis_events")
                count = cursor.fetchone()[0]
            print(f"  Database: OK ({count} events)")
        except Exception as e:
            print(f"  Database: FAILED - {e}")
            return False

        # Test health monitoring
        try:
            snapshot = self.health_monitor.get_health_snapshot()
            print(f"  Health Monitor: OK (CPU={snapshot.get('cpu_percent', 0):.1f}%)")
        except Exception as e:
            print(f"  Health Monitor: FAILED - {e}")
            return False

        print("\nAll systems operational")
        return True
