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
from core.intent_parser import IntentParser, IntentParseError
from automation.executor import ActionExecutor


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

        # Day 2: Initialize intent parser and executor
        # Day 3: Support dry_run mode from settings
        dry_run = settings.get("safety", {}).get("dry_run", False)
        self.intent_parser = IntentParser(logger=logger)
        self.executor = ActionExecutor(logger=logger, settings=settings, dry_run=dry_run)

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

                # Day 2: PARSE phase - Convert reasoning to Intent object
                print(f"\n{'=' * 60}")
                print("INTENT PARSING:")
                print(f"{'=' * 60}\n")

                parsed_intent = self._parse_intent(reasoning, prompt)

                if parsed_intent:
                    print(f"[Parser] Intent: {parsed_intent.action_type.value}")
                    print(f"[Parser] Parameters: {parsed_intent.parameters}")
                    print(f"[Parser] Rationale: {parsed_intent.rationale}")

                    # Day 2: PLAN phase - Create action plan
                    print(f"\n{'=' * 60}")
                    print("ACTION PLANNING:")
                    print(f"{'=" * 60}\n")

                    action_plan = self.action_planner.plan(parsed_intent)
                    print(f"[Planner] Created plan with {len(action_plan.steps)} steps")
                    for step in action_plan.steps:
                        print(f"  {step.step_id}. {step.description}")

                    # Day 2: POLICY CHECK phase
                    print(f"\n{'=' * 60}")
                    print("POLICY CHECK:")
                    print(f"{'=' * 60}\n")

                    policy_decision = self.policy_engine.check_intent(parsed_intent)
                    print(f"[Policy] Decision: {policy_decision}")

                    # Day 3: EXECUTE phase (REAL EXECUTION)
                    if policy_decision.allowed:
                        print(f"\n{'=' * 60}")
                        mode_label = "DRY RUN" if self.executor.dry_run else "EXECUTING"
                        print(f"{mode_label}:")
                        print(f"{'=' * 60}\n")

                        # Day 3: Real execution
                        try:
                            result = self.executor.execute_plan(action_plan)
                            print(f"\n[Execution] {'DRY RUN ' if self.executor.dry_run else ''}Result: {'SUCCESS' if result.success else 'FAILED'}")
                            if result.error:
                                print(f"[Execution] Error: {result.error}")
                            if result.output:
                                print(f"[Execution] Output: {result.output}")
                            print(f"[Execution] Time: {result.execution_time_ms:.2f}ms")
                        except Exception as e:
                            print(f"[Execution] FAILED: {e}")
                            self.logger.log_event(
                                event_type="execution_failed",
                                data={"error": str(e)},
                                status="error"
                            )
                    else:
                        print(f"\n[Policy] Action blocked: {policy_decision.reason}")
                        if policy_decision.requires_approval:
                            print(f"[Policy] Human approval required")

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

    def _parse_intent(self, llm_output: str, prompt: str) -> Optional['Intent']:
        """
        Parse LLM output into Intent object.

        Day 2: Parses both JSON and natural language.

        Args:
            llm_output: Raw LLM output (reasoning text)
            prompt: Original task prompt

        Returns:
            Parsed Intent object or None if parsing fails
        """
        try:
            # Try to parse LLM output as intent
            intent = self.intent_parser.parse(llm_output)

            self.logger.log_event(
                event_type="intent_parsed",
                data={
                    "intent_type": intent.action_type.value,
                    "parameters": intent.parameters
                },
                status="success"
            )

            return intent

        except IntentParseError as e:
            # If parsing fails, fall back to creating a simple screenshot intent
            # This allows the control loop to continue even if LLM output is unclear
            self.logger.log_event(
                event_type="intent_parse_failed",
                data={"error": str(e), "llm_output": llm_output[:200]},
                status="warning"
            )
            print(f"[Parser] WARNING: Could not parse intent: {e}")
            print(f"[Parser] Falling back to screenshot intent")

            # Create fallback intent
            from intents.intent_schema import Intent
            from intents.intent_types import IntentType

            return Intent(
                action_type=IntentType.SCREENSHOT,
                parameters={"output_path": "fallback_screenshot.png"},
                rationale="Fallback intent due to parsing failure"
            )
