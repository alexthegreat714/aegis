"""
OpenWebUI API client.

Mirrors the Chess agent's API calling pattern.
"""

from typing import Dict, Any, List, Optional
from pathlib import Path
import requests
import json


class OWUIClient:
    """
    Client for calling local OpenWebUI API.

    Uses the same pattern as the Chess agent:
    POST http://127.0.0.1:3000/api/chat/completions
    """

    def __init__(self, base_url: str, endpoint: str, token_file: str, timeout: int = 30, default_model: str = "agentica-org_DeepCoder-14B-Preview-Q8_0:latest"):
        """
        Initialize OWUI client.

        Args:
            base_url: Base URL (e.g., "http://127.0.0.1:3000")
            endpoint: API endpoint (e.g., "/api/chat/completions")
            token_file: Path to file containing Bearer token
            timeout: Request timeout in seconds
            default_model: Default model name to use
        """
        self.base_url = base_url.rstrip('/')
        self.endpoint = endpoint
        self.token_file = Path(token_file)
        self.timeout = timeout
        self.default_model = default_model
        self.token: Optional[str] = None

        self._load_token()

    def _load_token(self) -> None:
        """Load Bearer token from file."""
        try:
            if self.token_file.exists():
                with open(self.token_file, 'r') as f:
                    self.token = f.read().strip()
                print(f"[OWUI] Token loaded from {self.token_file}")
            else:
                print(f"[OWUI] Warning: Token file not found at {self.token_file}")
                print("[OWUI] Create token file or API calls will fail")
        except Exception as e:
            print(f"[OWUI] Error loading token: {e}")

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = None,
        temperature: float = 0.2,
        max_tokens: int = 2000,
        stream: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Call chat completion API (Chess agent compatible format).

        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model name (default: "aegis")
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            stream: Enable streaming response
            **kwargs: Additional parameters

        Returns:
            API response dictionary

        Raises:
            requests.RequestException: If API call fails
        """
        if not self.token:
            raise RuntimeError("No API token available. Check token_file configuration.")

        # Use default model if none specified
        if model is None:
            model = self.default_model

        url = f"{self.base_url}{self.endpoint}"

        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

        # Chess agent compatible payload format
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "stream": stream,
            **kwargs
        }

        # Add max_tokens only if provided (some models don't support it)
        if max_tokens:
            payload["max_tokens"] = max_tokens

        try:
            if stream:
                return self._stream_completion(url, headers, payload)
            else:
                response = requests.post(
                    url,
                    headers=headers,
                    data=json.dumps(payload),
                    timeout=self.timeout
                )
                response.raise_for_status()
                return response.json()

        except requests.RequestException as e:
            print(f"[OWUI] API call failed: {e}")
            raise

    def _stream_completion(
        self,
        url: str,
        headers: Dict[str, str],
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle streaming completion response.

        Args:
            url: API endpoint URL
            headers: Request headers
            payload: Request payload

        Returns:
            Accumulated response dictionary
        """
        accumulated_content = ""

        with requests.post(
            url,
            headers=headers,
            data=json.dumps(payload),
            stream=True,
            timeout=60
        ) as r:
            r.raise_for_status()

            for line in r.iter_lines(decode_unicode=True):
                if not line or not line.startswith("data: "):
                    continue

                chunk = line[len("data: "):]

                if chunk == "[DONE]":
                    break

                try:
                    chunk_data = json.loads(chunk)
                    delta_content = chunk_data.get("choices", [{}])[0].get("delta", {}).get("content", "")
                    accumulated_content += delta_content

                    # Optional: yield chunks for progress display
                    # print(delta_content, end="", flush=True)

                except json.JSONDecodeError:
                    continue

        # Return in standard format
        return {
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": accumulated_content
                },
                "finish_reason": "stop"
            }]
        }

    def simple_prompt(self, prompt: str, model: str = None) -> str:
        """
        Send a simple prompt and get text response.

        Args:
            prompt: User prompt
            model: Model name (default: "aegis")

        Returns:
            Response text
        """
        messages = [{"role": "user", "content": prompt}]

        response = self.chat_completion(messages=messages, model=model)

        # Parse standard Chess agent / OpenAI response format
        try:
            return response["choices"][0]["message"]["content"]
        except (KeyError, IndexError):
            print(f"[OWUI] Unexpected response format: {response}")
            return str(response)

    def prompt_with_context(
        self,
        prompt: str,
        context: Dict[str, Any],
        model: str = None,
        system_prompt: Optional[str] = None
    ) -> str:
        """
        Send prompt with structured context (Aegis reasoning format).

        Args:
            prompt: User prompt
            context: Context dictionary (observations, state, etc.)
            model: Model name (default: "aegis")
            system_prompt: Optional custom system prompt

        Returns:
            Response text
        """
        # Format context into system message
        if not system_prompt:
            system_prompt = (
                "You are Aegis, a local security/devops AI agent. "
                "Respond in concise JSON when asked to propose actions; "
                "include risks, tests, and diffs."
            )

        context_str = json.dumps(context, indent=2)

        messages = [
            {
                "role": "system",
                "content": f"{system_prompt}\n\nCurrent context:\n{context_str}"
            },
            {
                "role": "user",
                "content": prompt
            }
        ]

        response = self.chat_completion(messages=messages, model=model)

        try:
            return response["choices"][0]["message"]["content"]
        except (KeyError, IndexError):
            return str(response)

    def aegis_reasoning_call(
        self,
        task: str,
        observations: Dict[str, Any],
        conversation_history: List[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Call Aegis model for reasoning and action proposal.

        Args:
            task: Current task description
            observations: System observations
            conversation_history: Optional prior conversation

        Returns:
            Parsed reasoning response with actions
        """
        system_prompt = (
            "You are Aegis, a local security/devops AI agent.\n\n"
            "Your responses should follow this structure:\n"
            "1. **Reasoning**: Explain your thought process\n"
            "2. **Risk Assessment**: Low/Medium/High + justification\n"
            "3. **Proposed Actions**: List of intents with parameters\n"
            "4. **Tests**: How to verify success\n"
            "5. **Rollback**: How to undo if needed\n\n"
            "Be verbose in reasoning, concise in action specs."
        )

        messages = [
            {"role": "system", "content": system_prompt},
        ]

        # Add conversation history if provided
        if conversation_history:
            messages.extend(conversation_history)

        # Add current task with observations
        obs_str = json.dumps(observations, indent=2)
        task_message = (
            f"**Task**: {task}\n\n"
            f"**Current State**:\n```json\n{obs_str}\n```\n\n"
            f"What should we do next?"
        )

        messages.append({"role": "user", "content": task_message})

        # Call OWUI (uses default model)
        response = self.chat_completion(messages=messages, model=None, temperature=0.2)

        content = response["choices"][0]["message"]["content"]

        return {
            "reasoning": content,
            "raw_response": response,
            "model": "aegis"
        }

    def test_connection(self) -> bool:
        """
        Test API connection with default model.

        Returns:
            True if connection successful
        """
        try:
            response = self.simple_prompt("Say 'Aegis online' and nothing else.")
            print(f"[OWUI] Connection test successful: {response[:50]}...")
            return True
        except Exception as e:
            print(f"[OWUI] Connection test failed: {e}")
            return False
