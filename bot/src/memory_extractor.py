import re
from typing import Any, Dict, List


class MemoryExtractor:
    def __init__(self, kg=None):
        self.kg = kg
        self.major_aliases = {
            "自动化": "自动化专业",
            "自动化专业": "自动化专业",
            "智科": "智能科学与技术专业",
            "智能科学": "智能科学与技术专业",
            "智能科学与技术": "智能科学与技术专业",
            "智能科学与技术专业": "智能科学与技术专业",
            "通信": "通信工程专业",
            "通信工程": "通信工程专业",
            "通信工程专业": "通信工程专业"
        }
        self.goal_keywords = ["考研", "保研", "就业", "竞赛", "转专业", "出国", "实习", "读研"]
        self.interest_keywords = [
            "人工智能", "AI", "机器学习", "深度学习", "知识图谱", "机器人", "控制", "自动控制",
            "嵌入式", "单片机", "通信", "信号处理", "图像处理", "数据挖掘", "算法", "软件开发"
        ]
        self.style_keywords = {
            "详细": "详细解释",
            "简单": "简洁回答",
            "通俗": "通俗解释",
            "表格": "表格呈现",
            "路线": "路径式建议",
            "规划": "规划式建议"
        }

    def extract(self, question: str, answer: str = "") -> Dict[str, Any]:
        text = question or ""
        result = {
            "major": "",
            "grade": "",
            "interests": [],
            "goals": [],
            "learned_courses": [],
            "weak_courses": [],
            "preferred_style": [],
            "summaries": []
        }

        result["major"] = self._extract_major(text)
        result["grade"] = self._extract_grade(text)
        result["interests"] = self._extract_by_keywords(text, self.interest_keywords)
        result["goals"] = self._extract_by_keywords(text, self.goal_keywords)
        result["preferred_style"] = self._extract_styles(text)
        result["learned_courses"] = self._extract_courses_by_patterns(text, ["学过", "已经学", "已学", "上过", "修过"])
        result["weak_courses"] = self._extract_courses_by_patterns(text, ["薄弱", "不会", "不懂", "困难", "吃力", "差", "没学好"])
        result["summaries"] = self._build_summaries(result)

        return result

    def _extract_major(self, text: str) -> str:
        for alias, major in self.major_aliases.items():
            if alias in text and any(marker in text for marker in ["我是", "我学", "我的专业", "专业是", "学生"]):
                return major
        return ""

    def _extract_grade(self, text: str) -> str:
        patterns = [
            r"大[一二三四五]",
            r"研[一二三]",
            r"[一二三四五]年级",
            r"本科[一二三四]年级"
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(0)
        return ""

    def _extract_by_keywords(self, text: str, keywords: List[str]) -> List[str]:
        return [keyword for keyword in keywords if keyword in text]

    def _extract_styles(self, text: str) -> List[str]:
        styles = []
        for keyword, style in self.style_keywords.items():
            if keyword in text:
                styles.append(style)
        return styles

    def _extract_courses_by_patterns(self, text: str, markers: List[str]) -> List[str]:
        courses = self._known_courses()
        matched = []
        clauses = [clause for clause in re.split(r"[，。！？；;]|但是|但|不过|然后", text) if clause]

        for clause in clauses:
            if not any(marker in clause for marker in markers):
                continue
            for course in courses:
                clean_course = self._normalize_text(course)
                if clean_course in clause and clean_course not in matched:
                    matched.append(clean_course)

        short_patterns = [
            r"(?:学过|已经学|已学|上过|修过|不会|不懂|薄弱|困难|吃力|没学好)([^，。！？；;、但 ]{2,20})",
            r"([^，。！？；;、但 ]{2,20})(?:学过|已经学|已学|上过|修过|不会|不懂|薄弱|困难|吃力|没学好)"
        ]
        for clause in clauses:
            if not any(marker in clause for marker in markers):
                continue
            for pattern in short_patterns:
                for match in re.findall(pattern, clause):
                    value = self._clean_course_name(match)
                    if value and value not in matched and not self._is_noise(value):
                        matched.append(value)

        return matched[:10]

    def _clean_course_name(self, value: str) -> str:
        value = self._normalize_text(value)
        for word in ["比较", "有点", "很", "非常", "特别", "这门课", "课程"]:
            value = value.replace(word, "")
        value = self._normalize_text(value)
        aliases = {
            "概率论": "概率论",
            "线代": "线性代数",
            "高数": "高等数学",
            "数据结构": "数据结构",
            "机器学习": "机器学习",
            "知识图谱": "知识图谱"
        }
        for alias, course in aliases.items():
            if alias in value:
                return course
        return value

    def _normalize_text(self, value: str) -> str:
        return re.sub(r"\s+", "", value.replace("\u3000", " ")).strip()

    def _known_courses(self) -> List[str]:
        if self.kg is None:
            return []

        courses = set()
        for triple in self.kg.triples:
            if triple.get("subject_type") == "课程":
                courses.add(self._normalize_text(triple.get("subject", "")))
            if triple.get("object_type") == "课程":
                courses.add(self._normalize_text(triple.get("object", "")))
        return sorted([course for course in courses if course], key=len, reverse=True)

    def _build_summaries(self, result: Dict[str, Any]) -> List[str]:
        summaries = []
        if result.get("major"):
            summaries.append(f"学生专业为{result['major']}")
        if result.get("interests"):
            summaries.append(f"学生关注{self._join(result['interests'])}方向")
        if result.get("goals"):
            summaries.append(f"学生目标包含{self._join(result['goals'])}")
        if result.get("weak_courses"):
            summaries.append(f"学生在{self._join(result['weak_courses'])}上存在薄弱点")
        return summaries

    def _is_noise(self, value: str) -> bool:
        noise_words = ["什么", "哪些", "怎么", "应该", "感觉", "但是", "如果"]
        return any(word in value for word in noise_words)

    def _join(self, values: List[str]) -> str:
        return "、".join(values)
