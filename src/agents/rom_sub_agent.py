import json
import logging
from typing import Dict, Any, Tuple
from core.llm_client import LLMClient
from core.prompts import load_prompt
from db.local_database import LocalDatabase

logger = logging.getLogger(__name__)

class RomSubAgent:
    """
    ROM Sub Agent wrapper.
    Receives specific targets and hints, and autonomously loops using 
    tool calls (vector_search, absolute_search) until it finds the answer.
    """
    def __init__(self, llm_client: LLMClient, db: LocalDatabase):
        self.llm_client = llm_client
        self.db = db
        self.system_prompt = load_prompt("rom_sub_skill.md")

        # Define native tools for OpenRouter/OpenAI API
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "vector_search",
                    "description": "意味的な関連度に基づいてチャットログや設定資料を検索します（RAGの基本検索）。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "検索キーワード"},
                            "top_k": {"type": "integer", "description": "取得件数（デフォルト: 2）"}
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "absolute_search",
                    "description": "指定されたログIDの前後を時系列で取得します。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "target_log_id": {"type": "string", "description": "起点となるログID"},
                            "radius": {"type": "integer", "description": "前後取得件数（デフォルト: 1）"}
                        },
                        "required": ["target_log_id"]
                    }
                }
            }
        ]

    async def process(self, sub_task: Dict[str, Any]) -> Dict[str, Any]:
        logger.info(f"\n=== [ROM Sub Agent] Starting Task: {sub_task.get('task_id')} ===")
        user_prompt = f"```json\n{json.dumps(sub_task, ensure_ascii=False, indent=2)}\n```"
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        full_raw_cot = ""
        MAX_LOOPS = 5
        for loop_count in range(MAX_LOOPS):
            logger.info(f"[ROM Sub Agent] Tool Loop Iteration {loop_count + 1}...")
            parsed_json, msg, raw_output = await self.llm_client.chat_with_tools(
                messages=messages,
                tools=self.tools
            )

            # IF HTTP/API Error 
            if not msg:
                logger.warning(f"[ROM Sub Agent] API Error (rate limit etc). Retrying... ({loop_count}/{MAX_LOOPS})")
                import asyncio
                await asyncio.sleep(5)
                continue

            # Keep context by dict-ifying the message and injecting reasoning if present
            msg_dict = {"role": "assistant", "content": msg.content or ""}
            reasoning_text = getattr(msg, "reasoning", "")
            
            # Store the thought process for the final JSON artifact
            if reasoning_text:
                full_raw_cot += f"\n[Turn {loop_count+1} Reasoning]\n{reasoning_text}\n"
            if msg.content:
                full_raw_cot += f"\n[Turn {loop_count+1} Content]\n{msg.content}\n"
                
            if reasoning_text:
                # OpenRouter recommendation: preserve reasoning by prepending it to content
                msg_dict["content"] = f"<think>\n{reasoning_text}\n</think>\n\n" + msg_dict["content"]
            
            if msg.tool_calls:
                msg_dict["tool_calls"] = [{"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments}} for tc in msg.tool_calls]
            
            messages.append(msg_dict)

            # If LLM triggered tools
            if msg.tool_calls:
                for tool_call in msg.tool_calls:
                    func_name = tool_call.function.name
                    try:
                        args = json.loads(tool_call.function.arguments)
                    except json.JSONDecodeError:
                        args = {}
                        logger.error("[ROM Sub Agent] Failed to parse tool arguments.")
                    
                    logger.debug(f"[ROM Sub Agent] Calling tool {func_name} with {args}")
                    
                    if func_name == "vector_search":
                        res = await self.db.vector_search(args.get("query", ""), args.get("top_k", 2))
                    elif func_name == "absolute_search":
                        res = await self.db.absolute_search(args.get("target_log_id", ""), args.get("radius", 1))
                    else:
                        res = {"error": "Unknown tool"}

                    logger.debug(f"[ROM Sub Agent] Tool Result: {res}")
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": func_name,
                        "content": json.dumps(res, ensure_ascii=False)
                    })
            # If LLM output final JSON reporting success/not_found
            elif parsed_json:
                logger.info(f"=== [ROM Sub Agent] Task {sub_task.get('task_id')} Completed ===")
                parsed_json["_raw_cot"] = full_raw_cot
                return parsed_json
            else:
                logger.warning("[ROM Sub Agent] No tool called and no JSON block returned. Prompting agent to correct...")
                messages.append({
                    "role": "user",
                    "content": "利用可能な検索ツールを呼び出すか、もしくは検索が完了した場合は必ず ```json で囲まれた最終報告のJSONブロックを出力してください。"
                })
                
        # Fallback if loops max out
        return {
            "task_id": sub_task.get('task_id'),
            "status": "not_found",
            "found_information": "Failed: Max search loops reached.",
            "referenced_log_ids": [],
            "_raw_cot": full_raw_cot
        }
