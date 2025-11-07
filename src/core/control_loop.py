"""
Main control loop for Aegis agent.

Implements the observe → think → decide → act cycle.
"""

from typing import Optional, Dict, Any, List
import time
from datetime import datetime
from pathlib import Path

from clients.owui_client import OWUIClient
from aegis_logging.logger import AegisLogger
from core.policy_engine import PolicyEngine
from core.action_planner import ActionPlanner
from core.reasoning import ReasoningChannel
from core.action_router import ActionRouter
from core.sandbox_revision import SandboxRevisionManager
from core.interactive import InteractivePause


class ControlLoop:
    """
    Main agent control loop.

    Coordinates between LLM, policy engine, action planner, and automation systems.
    """

    def __init__(
        self,
        settings: Dict[str, Any],
        policy_engine: PolicyEngine,
        logger: AegisLogger,
        owui_client: OWUIClient,
        action_planner: ActionPlanner,
        sandbox_manager: Optional[SandboxRevisionManager] = None,
        interactive_pause: Optional[InteractivePause] = None
    ):
        """
        Initialize control loop.

        Args:
            settings: System settings from settings.yaml
            policy_engine: Policy enforcement engine
            logger: Logging system
            owui_client: OpenWebUI API client
            action_planner: Action planning system
            sandbox_manager: Sandbox revision manager (optional)
            interactive_pause: Interactive pause system (optional)
        """
        self.settings = settings
        self.policy_engine = policy_engine
        self.logger = logger
        self.owui_client = owui_client
        self.action_planner = action_planner

        # Initialize Phase 5 components
        self.reasoning_channel = ReasoningChannel(logger=logger)

        # Initialize sandbox manager if not provided
        if sandbox_manager is None:
            sandbox_manager = SandboxRevisionManager(logger=logger)
        self.sandbox_manager = sandbox_manager

        # Initialize interactive pause if not provided
        if interactive_pause is None:
            interactive_pause = InteractivePause(logger=logger)
        self.interactive_pause = interactive_pause

        # Initialize action router
        self.action_router = ActionRouter(
            logger=logger,
            policy_engine=policy_engine,
            sandbox_manager=sandbox_manager,
            interactive_pause=interactive_pause,
            settings=settings
        )

        self.running = False
        self.iteration_count = 0
        self.max_iterations = settings.get("control_loop", {}).get("max_iterations", 100)

    def start(self, initial_prompt: Optional[str] = None) -> None:
        """
        Start the control loop.

        Args:
            initial_prompt: Optional initial prompt to seed the agent
        """
        self.running = True
        self.iteration_count = 0

        self.logger.log_event(
            event_type="control_loop_start",
            data={"initial_prompt": initial_prompt},
            status="info"
        )

        print("[Aegis] Control loop started")

        try:
            while self.running and self.iteration_count < self.max_iterations:
                self._run_iteration(initial_prompt if self.iteration_count == 0 else None)
                self.iteration_count += 1

                # Sleep between iterations
                sleep_ms = self.settings.get("control_loop", {}).get("sleep_between_actions_ms", 500)
                time.sleep(sleep_ms / 1000.0)

        except KeyboardInterrupt:
            print("\n[Aegis] Control loop interrupted by user")
            self.stop()
        except Exception as e:
            self.logger.log_event(
                event_type="control_loop_error",
                data={"error": str(e)},
                status="error"
            )
            raise
        finally:
            self.stop()

    def stop(self) -> None:
        """Stop the control loop gracefully."""
        self.running = False
        self.logger.log_event(
            event_type="control_loop_stop",
            data={"iterations_completed": self.iteration_count},
            status="info"
        )
        print(f"[Aegis] Control loop stopped after {self.iteration_count} iterations")

    def _run_iteration(self, prompt: Optional[str] = None) -> None:
        """
        Run a single iteration of the control loop (Phase 5 enhanced).

        Steps:
        1. Observe: Gather current state
        2. Think: Call LLM for internal reasoning (verbose, logged only)
        3. Summarize: Convert reasoning to compact intent packet
        4. Decide: Route intent through policy/sandbox/pause
        5. Act: Execute if allowed

        Args:
            prompt: Optional prompt for this iteration
        """
        # OBSERVE phase
        observation = self._observe()

        # THINK phase (LLM call - internal reasoning channel)
        if prompt:
            print(f"\n{'=' * 60}")
            print("REASONING (Internal - Logged Only):")
            print(f"{'=' * 60}\n")

            response = self._think(prompt, observation)

            if response:
                reasoning = response.get("reasoning", "")
                model = response.get("model", "unknown")

                # Display reasoning to terminal (Alex can see it)
                print(reasoning)
                print(f"\n{'=' * 60}\n")

                # Log internal reasoning (NEVER sent to Claude)
                reasoning_id = self.reasoning_channel.log_internal_reasoning(
                    task=prompt,
                    reasoning=reasoning,
                    model=model,
                    observation=observation
                )

                print(f"[Reasoning] Logged to internal channel: {reasoning_id}")

                # SUMMARIZE phase: Convert to compact intent packet
                intent = self.reasoning_channel.summarize_to_intent(
                    reasoning=reasoning,
                    task=prompt
                )

                if intent:
                    intent_id = self.reasoning_channel.log_external_intent(intent)
                    print(f"[Intent] Created external intent: {intent_id}")
                    print(f"[Intent] Type: {intent.get('intent_type')}, Risk: {intent.get('risk_level')}")

                    # DECIDE & ACT phase: Route through action router
                    print(f"\n{'=' * 60}")
                    print("ROUTING INTENT:")
                    print(f"{'=' * 60}\n")

                    routing_result = self.action_router.route_intent(intent)

                    print(f"[Router] Status: {routing_result.get('status')}")
                    print(f"[Router] {routing_result.get('message', routing_result.get('reason', 'Done'))}")

                    if routing_result.get("status") == "sandboxed":
                        print(f"[Router] Revision ID: {routing_result.get('revision_id')}")
                        print(f"[Router] Use: python aegis.py --approve-revision {routing_result.get('revision_id')}")

                print("\n[Aegis] Iteration completed. Stopping control loop.")
                self.stop()
            else:
                print("[Aegis] No response from LLM. Continuing...")

        else:
            # No prompt means we're past the first iteration
            self.stop()

    def _observe(self) -> Dict[str, Any]:
        """
        Gather current system state.

        Returns:
            Dictionary containing current observations
        """
        import psutil
        import platform

        observation = {
            "timestamp": datetime.now().isoformat(),
            "iteration": self.iteration_count,
            "screenshot": None,  # Screenshot capture disabled for now (requires UI automation)
            "active_window": self._get_active_window(),
            "recent_logs": self._get_recent_logs(limit=5),
            "system_status": {
                "cpu_percent": psutil.cpu_percent(interval=0.1),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_percent": psutil.disk_usage('/').percent,
                "running": self.running,
                "platform": platform.system(),
                "python_version": platform.python_version()
            },
            "processes": self._get_process_summary()
        }

        self.logger.log_event(
            event_type="observation_gathered",
            data={
                "iteration": self.iteration_count,
                "cpu_percent": observation["system_status"]["cpu_percent"],
                "memory_percent": observation["system_status"]["memory_percent"]
            },
            status="info"
        )

        return observation

    def _get_active_window(self) -> Optional[str]:
        """
        Get active window title (Windows-specific).

        Returns:
            Window title or None if detection fails
        """
        try:
            import pygetwindow as gw
            active = gw.getActiveWindow()
            if active:
                return active.title
        except Exception as e:
            # Window detection not critical, continue without it
            pass
        return None

    def _get_recent_logs(self, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Query recent log entries from SQLite.

        Args:
            limit: Number of recent logs to retrieve

        Returns:
            List of recent log entries
        """
        try:
            # Query from SQLite using logger
            import sqlite3
            db_path = self.settings.get("paths", {}).get("db_path", "data/aegis.db")

            if not Path(db_path).exists():
                return []

            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT timestamp, event_type, status
                FROM events
                ORDER BY id DESC
                LIMIT ?
            """, (limit,))

            rows = cursor.fetchall()
            conn.close()

            return [
                {"timestamp": row[0], "event_type": row[1], "status": row[2]}
                for row in rows
            ]
        except Exception:
            return []

    def _get_process_summary(self) -> Dict[str, Any]:
        """
        Get summary of running processes.

        Returns:
            Process summary dictionary
        """
        try:
            import psutil
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent']):
                try:
                    processes.append({
                        "pid": proc.info['pid'],
                        "name": proc.info['name'],
                        "cpu_percent": proc.info['cpu_percent']
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

            # Return top 5 CPU consumers
            processes.sort(key=lambda x: x.get('cpu_percent', 0) or 0, reverse=True)
            return {
                "total_count": len(processes),
                "top_consumers": processes[:5]
            }
        except Exception:
            return {"total_count": 0, "top_consumers": []}

    def _think(self, prompt: str, observation: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Call LLM to determine next action.

        Args:
            prompt: User prompt or task description
            observation: Current system observations

        Returns:
            Intent dictionary or None if no action needed
        """
        try:
            # Call LLM via OWUI aegis_reasoning_call
            response = self.owui_client.aegis_reasoning_call(
                task=prompt,
                observations=observation,
                conversation_history=[]  # TODO: Track conversation history
            )

            # Log LLM call
            self.logger.log_llm_call(
                model=response.get("model", "unknown"),
                prompt=prompt,
                response=response.get("reasoning", ""),
                tokens_used=0  # TODO: Parse token count from response
            )

            # TODO: Parse response into Intent objects
            # For now, return raw reasoning response
            return response

        except Exception as e:
            self.logger.log_event(
                event_type="llm_call_failed",
                data={"prompt": prompt, "error": str(e)},
                status="error"
            )
            print(f"[Think] ERROR: LLM call failed: {e}")
            return None
