"""
Main control loop for Aegis agent.

Implements the observe → think → decide → act cycle.
Day 4: Multi-cycle autonomous operation with observation and digest reporting.
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
from utils.system_observer import SystemObserver
from reporting.digest import DigestGenerator


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

        # Day 4: Initialize observation and digest tracking
        self.system_observer = SystemObserver()
        self.digest_generator = DigestGenerator()

        self.running = False
        self.iteration_count = 0
        self.cycle_count = 0
        self.max_iterations = settings.get("control_loop", {}).get("max_iterations", 100)
        self.sleep_interval_ms = settings.get("control_loop", {}).get("sleep_between_actions_ms", 500)

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
            data={
                "iterations_completed": self.iteration_count,
                "cycles_completed": self.cycle_count
            },
            status="info"
        )
        print(f"[Aegis] Control loop stopped after {self.cycle_count} cycles ({self.iteration_count} iterations)")

    def run_forever(self, initial_prompt: Optional[str] = None) -> None:
        """
        Run control loop continuously until interrupted.

        Day 4: Multi-cycle autonomous operation with graceful shutdown.

        Args:
            initial_prompt: Optional initial prompt to seed the agent

        Note:
            Press CTRL+C to stop gracefully
        """
        self.running = True
        self.cycle_count = 0
        self.iteration_count = 0

        # Start digest tracking
        self.digest_generator.start_digest()

        self.logger.log_event(
            event_type="control_loop_start_forever",
            data={"initial_prompt": initial_prompt},
            status="info"
        )

        print("[Aegis] Control loop started (continuous mode)")
        print("[Aegis] Press CTRL+C to stop gracefully\n")

        try:
            while self.running:
                self._run_cycle(initial_prompt if self.cycle_count == 0 else None)
                self.cycle_count += 1

                # Sleep between cycles
                time.sleep(self.sleep_interval_ms / 1000.0)

        except KeyboardInterrupt:
            print("\n[Aegis] Control loop interrupted by user (CTRL+C)")
            self.stop()
        except Exception as e:
            self.logger.log_event(
                event_type="control_loop_error",
                data={"error": str(e)},
                status="error"
            )
            raise
        finally:
            # End digest and display
            if self.digest_generator.current_digest:
                digest = self.digest_generator.end_digest()
                print("\n" + "=" * 60)
                print(digest.to_markdown())
                print("=" * 60)

            self.stop()

    def run_n_cycles(self, n: int, initial_prompt: Optional[str] = None) -> None:
        """
        Run control loop for N cycles.

        Day 4: Fixed number of autonomous cycles.

        Args:
            n: Number of cycles to run
            initial_prompt: Optional initial prompt to seed the agent
        """
        self.running = True
        self.cycle_count = 0
        self.iteration_count = 0

        # Start digest tracking
        self.digest_generator.start_digest()

        self.logger.log_event(
            event_type="control_loop_start_n_cycles",
            data={"n_cycles": n, "initial_prompt": initial_prompt},
            status="info"
        )

        print(f"[Aegis] Control loop started ({n} cycles)\n")

        try:
            while self.running and self.cycle_count < n:
                self._run_cycle(initial_prompt if self.cycle_count == 0 else None)
                self.cycle_count += 1

                # Sleep between cycles (except after last cycle)
                if self.cycle_count < n:
                    time.sleep(self.sleep_interval_ms / 1000.0)

        except KeyboardInterrupt:
            print("\n[Aegis] Control loop interrupted by user (CTRL+C)")
            self.stop()
        except Exception as e:
            self.logger.log_event(
                event_type="control_loop_error",
                data={"error": str(e)},
                status="error"
            )
            raise
        finally:
            # End digest and display
            if self.digest_generator.current_digest:
                digest = self.digest_generator.end_digest()
                print("\n" + "=" * 60)
                print(digest.to_markdown())
                print("=" * 60)

            self.stop()

    def get_current_digest(self) -> Optional[Dict[str, Any]]:
        """
        Get current digest without ending the session.

        Day 4: Allow querying digest during execution.

        Returns:
            Current digest dictionary or None
        """
        digest = self.digest_generator.get_current_digest()
        return digest.to_dict() if digest else None

    def _run_cycle(self, prompt: Optional[str] = None) -> None:
        """
        Run a single cycle of the control loop.

        Day 4: Enhanced to support intent chaining and digest tracking.

        A cycle consists of:
        1. Observe: Gather system state
        2. Think: Call LLM for reasoning
        3. Parse: Extract intent list (may be multiple intents)
        4. For each intent:
           - Decide: Check policy
           - Plan: Create action plan
           - Act: Execute if allowed
        5. Track: Record results in digest

        Args:
            prompt: Optional prompt for this cycle
        """
        print(f"\n{'=' * 80}")
        print(f"CYCLE {self.cycle_count + 1}")
        print(f"{'=' * 80}\n")

        # OBSERVE phase - Use SystemObserver for enhanced context
        observation = self._observe_enhanced()

        # THINK phase (LLM call)
        if prompt:
            print(f"{'=' * 60}")
            print("REASONING:")
            print(f"{'=' * 60}\n")

            response = self._think(prompt, observation)

            if response:
                reasoning = response.get("reasoning", "")
                model = response.get("model", "unknown")

                # Display reasoning
                print(reasoning)
                print(f"\n{'=' * 60}\n")

                # Log internal reasoning
                reasoning_id = self.reasoning_channel.log_internal_reasoning(
                    task=prompt,
                    reasoning=reasoning,
                    model=model,
                    observation=observation
                )

                # Day 4: PARSE phase - Support intent chaining
                print(f"{'=' * 60}")
                print("INTENT PARSING (Chaining Support):")
                print(f"{'=' * 60}\n")

                intent_list = self._parse_intent_list(reasoning, prompt)

                if intent_list:
                    print(f"[Parser] Parsed {len(intent_list)} intent(s)")

                    # Day 4: Execute each intent in sequence
                    for idx, intent in enumerate(intent_list):
                        self.iteration_count += 1

                        print(f"\n{'—' * 60}")
                        print(f"INTENT {idx + 1}/{len(intent_list)}")
                        print(f"{'—' * 60}\n")

                        print(f"[Parser] Type: {intent.action_type.value}")
                        print(f"[Parser] Parameters: {intent.parameters}")
                        print(f"[Parser] Rationale: {intent.rationale}")

                        # PLAN phase
                        print(f"\n{'=' * 60}")
                        print("ACTION PLANNING:")
                        print(f"{'=' * 60}\n")

                        action_plan = self.action_planner.plan(intent)
                        print(f"[Planner] Created plan with {len(action_plan.steps)} steps")
                        for step in action_plan.steps:
                            print(f"  {step.step_id}. {step.description}")

                        # POLICY CHECK phase
                        print(f"\n{'=' * 60}")
                        print("POLICY CHECK:")
                        print(f"{'=' * 60}\n")

                        policy_decision = self.policy_engine.check_intent(intent)
                        print(f"[Policy] Decision: {policy_decision}")

                        # Track policy decision in digest
                        self.digest_generator.record_policy_decision(
                            allowed=policy_decision.allowed,
                            requires_approval=policy_decision.requires_approval
                        )

                        # EXECUTE phase
                        if policy_decision.allowed:
                            print(f"\n{'=' * 60}")
                            mode_label = "DRY RUN" if self.executor.dry_run else "EXECUTING"
                            print(f"{mode_label}:")
                            print(f"{'=' * 60}\n")

                            try:
                                result = self.executor.execute_plan(action_plan)
                                print(f"\n[Execution] {'DRY RUN ' if self.executor.dry_run else ''}Result: {'SUCCESS' if result.success else 'FAILED'}")
                                if result.error:
                                    print(f"[Execution] Error: {result.error}")
                                if result.output:
                                    print(f"[Execution] Output: {result.output}")
                                print(f"[Execution] Time: {result.execution_time_ms:.2f}ms")

                                # Track execution in digest
                                self.digest_generator.record_intent_executed(
                                    intent_type=intent.action_type.value,
                                    success=result.success,
                                    execution_time_ms=result.execution_time_ms,
                                    error=result.error
                                )

                            except Exception as e:
                                print(f"[Execution] FAILED: {e}")
                                self.logger.log_event(
                                    event_type="execution_failed",
                                    data={"error": str(e)},
                                    status="error"
                                )

                                # Track failure in digest
                                self.digest_generator.record_intent_executed(
                                    intent_type=intent.action_type.value,
                                    success=False,
                                    execution_time_ms=0.0,
                                    error=str(e)
                                )

                        else:
                            print(f"\n[Policy] Action blocked: {policy_decision.reason}")
                            if policy_decision.requires_approval:
                                print(f"[Policy] Human approval required")

                else:
                    print("[Parser] No intents parsed")

        else:
            # No prompt - skip this cycle
            print("[Aegis] No prompt for this cycle, skipping...")

        # Record cycle completion
        self.digest_generator.record_cycle()

        print(f"\n{'=' * 80}")
        print(f"CYCLE {self.cycle_count + 1} COMPLETED")
        print(f"{'=' * 80}\n")

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
                    print("=" * 60 + "\n")

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

    def _observe_enhanced(self) -> Dict[str, Any]:
        """
        Gather enhanced system state using SystemObserver.

        Day 4: Uses SystemObserver for structured, comprehensive observations.

        Returns:
            SystemObservation dictionary
        """
        observation = self.system_observer.observe()

        self.logger.log_event(
            event_type="observation_gathered",
            data={
                "cycle": self.cycle_count,
                "iteration": self.iteration_count,
                "cpu_percent": observation.get("cpu_percent"),
                "memory_percent": observation.get("memory_percent"),
                "active_window": observation.get("active_window")
            },
            status="info"
        )

        return observation

    def _parse_intent_list(self, llm_output: str, prompt: str) -> List['Intent']:
        """
        Parse LLM output into list of Intent objects.

        Day 4: Support intent chaining - LLM may return multiple intents.

        Args:
            llm_output: Raw LLM output (reasoning text)
            prompt: Original task prompt

        Returns:
            List of Intent objects (may be empty)
        """
        try:
            # Try to parse as intent list
            from intents.intent_schema import Intent

            intent_list = self.intent_parser.parse_intent_list(llm_output)

            if intent_list:
                self.logger.log_event(
                    event_type="intent_list_parsed",
                    data={
                        "intent_count": len(intent_list),
                        "intent_types": [i.action_type.value for i in intent_list]
                    },
                    status="success"
                )
                return intent_list

            # If no intents parsed, try single intent as fallback
            try:
                intent = self._parse_intent(llm_output, prompt)
                if intent:
                    return [intent]
            except Exception:
                pass

            return []

        except Exception as e:
            self.logger.log_event(
                event_type="intent_list_parse_failed",
                data={"error": str(e), "llm_output": llm_output[:200]},
                status="warning"
            )
            print(f"[Parser] WARNING: Could not parse intent list: {e}")
            return []
