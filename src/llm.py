"""
Module: LLM Interface Wrapper
Handles requests to Gemini API (via google-genai) with fallback support.
"""
import json
import re
from typing import Dict, Any, Optional
from src.config import GEMINI_API_KEY, GEMINI_MODEL


class LLMClient:
    """Wrapper for Google Gemini API."""

    def __init__(self, api_key: str = GEMINI_API_KEY, model_name: str = GEMINI_MODEL):
        self.api_key = api_key
        self.model_name = model_name
        self.client = None

        if self.api_key and self.api_key != "your_gemini_api_key_here":
            try:
                from google import genai
                self.client = genai.Client(api_key=self.api_key)
                print(f"[*] Initialized Gemini API client ({self.model_name}).")
            except Exception as e:
                print(f"[NOTE] Could not initialize Gemini API client: {e}")

    def generate_json(self, prompt: str) -> Optional[Dict[str, Any]]:
        """Sends prompt to Gemini API and parses response as JSON."""
        if self.client is None:
            return None

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            raw_text = response.text or ""

            # Clean JSON markdown fences
            clean_json = re.sub(r"^```json\s*", "", raw_text, flags=re.MULTILINE)
            clean_json = re.sub(r"```$", "", clean_json, flags=re.MULTILINE).strip()

            return json.loads(clean_json)
        except Exception as e:
            print(f"[WARNING] Gemini LLM API call failed: {e}")
            return None
