import os
import requests
from config import OLLAMA_URL, OLLAMA_MODEL


class OllamaClient:
    """
    HTTP client for querying local Ollama instance.
    """

    def __init__(self, url=None, model=None):
        self.url = (url or OLLAMA_URL or "http://localhost:11434").rstrip("/")
        self.model = model or OLLAMA_MODEL or "gemma3:1b"

    def generate(self, prompt: str, system: str = None, temperature: float = 0.0) -> str:
        """
        Send a generate request to the local Ollama instance.

        Parameters
        ----------
        prompt : str
            The user prompt.
        system : str, optional
            Optional system instructions.
        temperature : float, optional
            Temperature for generation (default is 0.0 for deterministic answers).

        Returns
        -------
        str
            The generated response content.
        """
        endpoint = f"{self.url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature
            }
        }
        if system:
            payload["system"] = system

        try:
            response = requests.post(endpoint, json=payload, timeout=180)
            if response.status_code == 200:
                return response.json().get("response", "").strip()
            else:
                return f"Error: Ollama returned status code {response.status_code}. Response: {response.text}"
        except requests.exceptions.RequestException as e:
            return f"Error: Failed to connect to Ollama at {self.url}. Please ensure Ollama is running. Details: {e}"
