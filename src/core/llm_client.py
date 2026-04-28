import os
import re
import json
import logging
from typing import Dict, Any, Optional, Tuple, List
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

class LLMClient:
    """
    Handles interactions with the LLM API via OpenRouter, including strictly parsing 
    the requested JSON blocks from the agent responses while keeping the CoT logs intact.
    """
    def __init__(self, model: str = "google/gemini-2.5-flash"):
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable is required.")
        
        self.client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key
        )
        self.model = model

    async def chat_with_tools(
        self, 
        messages: List[Dict[str, Any]], 
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> Tuple[Optional[Dict[str, Any]], Any, str]:
        """
        Sends conversational messages with optional tool definitions.
        Returns:
            parsed_json (Dict | None): If a final JSON block was found.
            response_msg (Any): The LLM's raw message object (contains tool_calls if any).
            raw_output (str): Text output.
        """
        try:
            kwargs = {
                "model": self.model,
                "messages": messages,
            }
            if tools:
                kwargs["tools"] = tools
            
            # Enable OpenRouter reasoning tokens for supported models
            if "gpt-oss" in self.model or "reasoning" in self.model.lower():
                kwargs["extra_body"] = {"include_reasoning": True}
            
            response = await self.client.chat.completions.create(**kwargs)
            msg = response.choices[0].message
            
            # OpenRouter passes reasoning natively in an extended attribute
            reasoning_text = getattr(msg, "reasoning", "")
            raw_output = msg.content or ""
            
            if reasoning_text:
                logger.info(f"\n[LLM Internal Reasoning]\n{reasoning_text}\n")
            
            # Extract JSON block if it decided to answer without tools
            parsed_json = None
            if not getattr(msg, "tool_calls", None):
                json_match = re.search(r'```json\n(.*?)\n```', raw_output, re.DOTALL)
                if json_match:
                    try:
                        parsed_json = json.loads(json_match.group(1))
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse JSON output: {e}")
            
            return parsed_json, msg, raw_output

        except Exception as e:
            logger.error(f"LLM API Call failed: {e}")
            return None, None, ""

    async def generate_json(self, system_prompt: str, user_prompt: str) -> Tuple[Optional[Dict[str, Any]], str]:
        """
        Legacy simple method for single-turn JSON generation (Main / ROM Main Agent).
        """
        parsed, _, raw = await self.chat_with_tools(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )
        return parsed, raw
