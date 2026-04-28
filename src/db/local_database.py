import sqlite3
import json
import os
import uuid
from datetime import datetime
from typing import Dict, Any, List

class LocalDatabase:
    """
    Handles connection to the local SQLite database for external ingested data,
    and also manages writing episodic memory logs (`_a`, `_b`, `_c`) to the filesystem.
    """
    def __init__(self, db_path: str = "gravity_data.db", logs_dir: str = "src/logs"):
        self.db_path = db_path
        self.logs_dir = logs_dir
        os.makedirs(self.logs_dir, exist_ok=True)
        self._init_db()
        
    def _init_db(self):
        """Initializes the SQLite schema for external data if it doesn't exist."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS external_data (
                id TEXT PRIMARY KEY,
                content TEXT,
                timestamp TEXT
            )
        ''')
        conn.commit()
        conn.close()

    def ingest_external_data(self, text: str, chunk_size: int = 300):
        """
        Splits text into chunks and saves them as external memory 
        that vectors/document searches can hit later.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        chunks = [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]
        timestamp = datetime.now().isoformat()
        
        for idx, chunk in enumerate(chunks):
            # Simplistic unique ID for demo
            chunk_id = f"ext-{uuid.uuid4().hex[:8]}-{idx}"
            cursor.execute('INSERT INTO external_data (id, content, timestamp) VALUES (?, ?, ?)', (chunk_id, chunk, timestamp))
            
        conn.commit()
        conn.close()
        print(f"Ingested {len(chunks)} chunks of external data.")

    def save_agent_log(self, log_id: str, agent_tier: str, content: Any):
        """
        Saves the agent's action and thought process into an individual JSON file
        based on the strictly formatted ID (_a, _b1, _c1).
        """
        file_path = os.path.join(self.logs_dir, f"{log_id}.json")
        
        data_to_save = {
            "log_id": log_id,
            "agent_tier": agent_tier,
            "timestamp": datetime.now().isoformat(),
            "content": content
        }
        
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data_to_save, f, ensure_ascii=False, indent=2)

    def _search_json_logs(self, query: str = None, start_time: str = None, end_time: str = None) -> List[Dict[str, Any]]:
        """Helper to scan past conversational logs stored as JSON."""
        results = []
        if not os.path.exists(self.logs_dir):
            return results
        
        for filename in os.listdir(self.logs_dir):
            if not filename.endswith(".json"):
                continue
            filepath = os.path.join(self.logs_dir, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                log_time = data.get("timestamp", "")
                
                # Time filters
                if start_time and log_time < start_time:
                    continue
                if end_time and log_time > end_time:
                    continue
                
                # Content filters (Stringify the content dict to search it)
                content_str = json.dumps(data.get("content", {}), ensure_ascii=False)
                if query and query not in content_str:
                    continue
                
                results.append({
                    "log_id": data.get("log_id"),
                    "content": content_str,
                    "timestamp": log_time
                })
            except Exception as e:
                print(f"Error reading log file {filename}: {e}")
                
        # Sort by timestamp ascending
        return sorted(results, key=lambda x: x["timestamp"])

    async def vector_search(self, query: str, top_k: int = 2) -> List[Dict[str, Any]]:
        # 1. Search external SQLite data
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id, content, timestamp FROM external_data WHERE content LIKE ?", ('%' + query + '%',))
        db_results = [{"log_id": row[0], "content": row[1], "timestamp": row[2]} for row in cursor.fetchall()]
        conn.close()
        
        # 2. Search dynamically generated past logs
        log_results = self._search_json_logs(query=query)
        
        # Combine and take top K
        combined = db_results + log_results
        
        # If absolutely empty, provide fallback stub for DB PoC robustness
        if not combined:
            return [
                 {"log_id": "mock-vec-1", "content": "星歴3年の冬、12月15日に〇〇村で事件が発生した。", "timestamp": "2023-12-10T10:00:00"},
                 {"log_id": "mock-vec-2", "content": "現場には古代文字が残されていた。魔導士ザンデの関与が疑われる。", "timestamp": "2023-12-16T09:00:00"}
            ]
        return combined[:top_k]

    async def absolute_search(self, start_time: str, end_time: str) -> List[Dict[str, Any]]:
        # 1. Search external SQLite data
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id, content, timestamp FROM external_data WHERE timestamp >= ? AND timestamp <= ?", (start_time, end_time))
        db_results = [{"log_id": row[0], "content": row[1], "timestamp": row[2]} for row in cursor.fetchall()]
        conn.close()
        
        # 2. Search dynamically generated past logs
        log_results = self._search_json_logs(start_time=start_time, end_time=end_time)
        
        combined = db_results + log_results
        
        if not combined:
            return [
                 {"log_id": "mock-abs-1", "content": "事件の第一発見者は村長の娘、リリアである。空が赤く染まっていたと証言。", "timestamp": "2023-12-15T15:30:00"}
            ]
        return combined
