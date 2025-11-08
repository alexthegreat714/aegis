"""
Claude prompt templates and builders for Aegis automation.

Provides structured prompts for different phases of development.
"""

from pathlib import Path
from typing import Optional, List, Dict, Any


def build_phase_c_prompt(
    goal: str,
    repo_summary: str,
    constraints: Optional[List[str]] = None
) -> str:
    """
    Build Phase C development prompt for Claude.

    Args:
        goal: Development goal/objective
        repo_summary: Summary of repository structure
        constraints: Optional list of constraints

    Returns:
        Formatted prompt string
    """
    constraints_list = constraints or [
        "No breaking changes to existing APIs",
        "All tests must remain passing",
        "New code must be import-safe with graceful errors for missing dependencies",
        "Use configuration toggles from settings.yaml",
        "Include comprehensive docstrings and logging"
    ]

    prompt = f"""# Aegis Development Task

## Goal
{goal}

## Repository Context
{repo_summary}

## Constraints
{chr(10).join(f'- {c}' for c in constraints_list)}

## Deliverables
1. Implement the requested functionality
2. Add comprehensive tests (unit tests with mocking)
3. Update documentation if needed
4. Ensure all existing tests remain passing

## Code Quality Requirements
- Clear docstrings for all public functions/classes
- Proper error handling with informative messages
- Logging at appropriate levels (INFO for major actions, DEBUG for details)
- Type hints where beneficial
- Windows-safe path handling (use Path everywhere)

## Testing Requirements
- New tests must be isolated and fast
- Use mocking for external dependencies (UI, network, etc.)
- Mark integration tests with @pytest.mark.vs to skip by default
- Verify all 171 existing tests still pass

Please implement this incrementally:
1. Create module structure with imports and basic classes
2. Implement core functionality
3. Add error handling and logging
4. Write tests
5. Verify integration

Show your work step-by-step and ask if anything is unclear.
"""

    return prompt


def build_code_review_prompt(
    code_snippet: str,
    context: str,
    review_type: str = "general"
) -> str:
    """
    Build code review prompt.

    Args:
        code_snippet: Code to review
        context: Context about the code
        review_type: Type of review (general, security, performance, etc.)

    Returns:
        Formatted prompt string
    """
    prompt = f"""# Code Review Request

## Context
{context}

## Review Type
{review_type}

## Code
```python
{code_snippet}
```

## Review Checklist
- Code correctness and logic
- Error handling completeness
- Type safety and edge cases
- Performance considerations
- Security implications
- Documentation quality
- Test coverage gaps

Please provide:
1. Issues found (if any) with severity (critical/major/minor)
2. Suggestions for improvement
3. Positive aspects worth noting
"""

    return prompt


def build_bug_fix_prompt(
    error_message: str,
    stack_trace: str,
    context: str
) -> str:
    """
    Build bug fix prompt.

    Args:
        error_message: Error message
        stack_trace: Full stack trace
        context: Context about when error occurs

    Returns:
        Formatted prompt string
    """
    prompt = f"""# Bug Fix Request

## Error
{error_message}

## Stack Trace
```
{stack_trace}
```

## Context
{context}

## Requirements
1. Identify root cause
2. Propose fix with explanation
3. Suggest tests to prevent regression
4. Consider edge cases and similar issues

Please provide:
1. Root cause analysis
2. Proposed fix (code changes)
3. Test cases to add
4. Prevention strategies
"""

    return prompt


def build_test_generation_prompt(
    module_path: str,
    function_signature: str,
    description: str
) -> str:
    """
    Build test generation prompt.

    Args:
        module_path: Path to module
        function_signature: Function signature to test
        description: Description of what function does

    Returns:
        Formatted prompt string
    """
    prompt = f"""# Test Generation Request

## Module
{module_path}

## Function
```python
{function_signature}
```

## Description
{description}

## Test Requirements
- Test happy path cases
- Test edge cases and boundaries
- Test error conditions
- Use appropriate mocking for dependencies
- Follow pytest best practices
- Use clear test names that describe what is being tested

Please generate:
1. Test class with setup/teardown if needed
2. Individual test methods for each scenario
3. Mock objects for external dependencies
4. Assertions that verify expected behavior

Format as ready-to-use pytest code.
"""

    return prompt


def build_repo_summary(repo_root: Path) -> str:
    """
    Build repository structure summary.

    Args:
        repo_root: Path to repository root

    Returns:
        Formatted summary string
    """
    repo_root = Path(repo_root)

    # Key directories to summarize
    key_dirs = {
        'src': 'Source code',
        'tests': 'Test suite',
        'config': 'Configuration files',
        'docs': 'Documentation',
        'revisions': 'Revision metadata',
    }

    summary_parts = ["## Repository Structure\n"]

    for dir_name, description in key_dirs.items():
        dir_path = repo_root / dir_name
        if dir_path.exists():
            file_count = len(list(dir_path.rglob('*.py')))
            summary_parts.append(f"- `{dir_name}/`: {description} ({file_count} Python files)")

    # List key modules
    src_dir = repo_root / 'src'
    if src_dir.exists():
        summary_parts.append("\n## Key Modules\n")
        for module_dir in sorted(src_dir.iterdir()):
            if module_dir.is_dir() and (module_dir / '__init__.py').exists():
                py_files = len(list(module_dir.glob('*.py')))
                summary_parts.append(f"- `src/{module_dir.name}/`: {py_files} modules")

    return '\n'.join(summary_parts)


def build_night_cycle_prompt(
    goal: str,
    round_num: int,
    prev_failures: Optional[List[str]] = None
) -> str:
    """
    Build prompt for night cycle autonomous development.

    Args:
        goal: Development goal
        round_num: Current round number
        prev_failures: Optional list of previous failures to address

    Returns:
        Formatted prompt string
    """
    prompt_parts = [
        f"# Aegis Night Cycle - Round {round_num}",
        f"\n## Goal\n{goal}",
    ]

    if prev_failures:
        prompt_parts.append("\n## Previous Round Failures")
        for i, failure in enumerate(prev_failures, 1):
            prompt_parts.append(f"{i}. {failure}")

        prompt_parts.append("\n## Focus")
        prompt_parts.append("Address the failures above before adding new functionality.")

    prompt_parts.append("\n## Requirements")
    prompt_parts.append("- All 171 base tests must pass")
    prompt_parts.append("- No breaking changes to existing APIs")
    prompt_parts.append("- Safe error handling with clear messages")
    prompt_parts.append("- Code ready for pytest validation")

    prompt_parts.append("\n## Deliverables")
    prompt_parts.append("1. Code changes (minimal, focused)")
    prompt_parts.append("2. Test coverage for changes")
    prompt_parts.append("3. Brief explanation of approach")

    return '\n'.join(prompt_parts)
