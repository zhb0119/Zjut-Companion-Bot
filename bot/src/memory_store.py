import json
import os
from datetime import datetime
from typing import Any, Dict, List


class MemoryStore:
    def __init__(self, memory_file: str = None):
        if memory_file is None:
            memory_file = os.path.join(os.path.dirname(__file__), '../data/student_memory.json')
        self.memory_file = os.path.abspath(memory_file)
        self.memory = self.load()

    def default_memory(self) -> Dict[str, Any]:
        return {
            "student_id": "default",
            "major": "",
            "grade": "",
            "interests": [],
            "goals": [],
            "learned_courses": [],
            "weak_courses": [],
            "preferred_style": [],
            "recent_questions": [],
            "summaries": [],
            "updated_at": ""
        }

    def load(self) -> Dict[str, Any]:
        if not os.path.exists(self.memory_file):
            memory = self.default_memory()
            self.save(memory)
            return memory

        with open(self.memory_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        memory = self.default_memory()
        memory.update(data)
        return memory

    def save(self, memory: Dict[str, Any] = None):
        if memory is None:
            memory = self.memory
        os.makedirs(os.path.dirname(self.memory_file), exist_ok=True)
        with open(self.memory_file, 'w', encoding='utf-8') as f:
            json.dump(memory, f, ensure_ascii=False, indent=2)

    def get(self) -> Dict[str, Any]:
        return self.memory

    def clear(self) -> Dict[str, Any]:
        self.memory = self.default_memory()
        self.memory["updated_at"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.save()
        return self.memory

    def apply_extraction(self, question: str, extracted: Dict[str, Any]) -> Dict[str, Any]:
        for key in ["major", "grade"]:
            value = extracted.get(key)
            if value:
                self.memory[key] = value

        for key in ["interests", "goals", "learned_courses", "weak_courses", "preferred_style", "summaries"]:
            self._merge_list(key, extracted.get(key, []))

        if question:
            self._append_limited("recent_questions", question, 20)

        self.memory["updated_at"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.save()
        return self.memory

    def format_for_prompt(self) -> str:
        memory = self.memory
        fields = []

        if memory.get("major"):
            fields.append(f"专业：{memory['major']}")
        if memory.get("grade"):
            fields.append(f"年级：{memory['grade']}")
        if memory.get("interests"):
            fields.append(f"兴趣方向：{self._join(memory['interests'])}")
        if memory.get("goals"):
            fields.append(f"学习目标：{self._join(memory['goals'])}")
        if memory.get("learned_courses"):
            fields.append(f"已学课程：{self._join(memory['learned_courses'])}")
        if memory.get("weak_courses"):
            fields.append(f"薄弱课程：{self._join(memory['weak_courses'])}")
        if memory.get("preferred_style"):
            fields.append(f"回答偏好：{self._join(memory['preferred_style'])}")
        if memory.get("summaries"):
            fields.append(f"长期摘要：{self._join(memory['summaries'][-5:])}")

        if not fields:
            return "学生长期记忆：暂无。"

        return "学生长期记忆：\n" + "\n".join(f"- {field}" for field in fields)

    def _merge_list(self, key: str, values: List[str]):
        if not values:
            return

        existing = self.memory.get(key, [])
        for value in values:
            if value and value not in existing:
                existing.append(value)
        self.memory[key] = existing[-30:]

    def _append_limited(self, key: str, value: str, limit: int):
        items = self.memory.get(key, [])
        items.append(value)
        self.memory[key] = items[-limit:]

    def _join(self, values: List[str]) -> str:
        return "、".join(values)
