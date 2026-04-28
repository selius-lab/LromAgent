import json
import logging
from typing import Dict, Any, Tuple
from core.llm_client import LLMClient
from core.prompts import load_prompt

logger = logging.getLogger(__name__)

class RomMainAgent:
    """
    ROM Main Agent wrapper.
    Responsible for receiving investigation requests, planning out parallel search tasks,
    and gathering results from ROM Sub Agents to build final reports.
    """
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client
        self.system_prompt = load_prompt("rom_main_skill.md")
        self.messages = [{"role": "system", "content": self.system_prompt}]

    def reset_memory(self):
        """Clears the conversational memory for a new investigation request."""
        self.messages = [{"role": "system", "content": self.system_prompt}]

    async def process(self, input_data: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
        user_prompt = f"```json\n{json.dumps(input_data, ensure_ascii=False, indent=2)}\n```"
        logger.info("\n=== [ROM Main Agent] Planning / Evaluating ===")
        
        self.messages.append({"role": "user", "content": user_prompt})
        parsed_json, msg, raw_output = await self.llm_client.chat_with_tools(self.messages)
        
        if msg:
            # Preserve history and reasoning
            msg_dict = {"role": "assistant", "content": msg.content or ""}
            reasoning_text = getattr(msg, "reasoning", "")
            if reasoning_text:
                msg_dict["content"] = f"<think>\n{reasoning_text}\n</think>\n\n" + msg_dict["content"]
            self.messages.append(msg_dict)
            
        logger.debug(f"[ROM Main Agent] Raw Output:\n{raw_output}")
        return parsed_json or {}, raw_output
