from typing import List, Dict, Any
from knowledge_graph import KnowledgeGraph


class RAGRetriever:
    def __init__(self, kg: KnowledgeGraph):
        self.kg = kg
        
        # 课程和专业别名映射表
        self.course_aliases = {
            # 专业简称（优先级高，放在前面）
            '通信专业': ['通信工程专业'],
            '通信工程': ['通信工程专业'],
            '通信': ['通信工程专业', '通信工程', '通信原理A', '通信原理'],
            '自动化专业': ['自动化专业'],
            '自动化': ['自动化专业', '自动化专业导论', '自动化技术前沿专题'],
            '智科专业': ['智能科学与技术专业'],
            '智科': ['智能科学与技术专业', '智能科学与技术'],
            '智能科学专业': ['智能科学与技术专业'],
            '智能科学': ['智能科学与技术专业', '智能科学与技术'],
            'AI专业': ['智能科学与技术专业'],
            
            # 课程简称
            '高数': ['高等数学Ⅰ', '高等数学II', '高等数学'],
            '线代': ['线性代数A', '线性代数'],
            '概率论': ['概率论与数理统计A', '概率论与数理统计'],
            '大物': ['大学物理Ⅰ', '大学物理ⅡB', '大学物理ⅡA', '大学物理'],
            '电路': ['电路原理A', '电路原理B', '电路原理'],
            'C++': ['面向对象C++编程A', '面向对象C++编程'],
            'Java': ['Java程序设计'],
            '数据结构': ['数据结构C'],
            '微机': ['微机原理A', '微机原理'],
            '单片机': ['单片机原理与实践'],
            '自控': ['自动控制原理B', '自动控制原理'],
            '现控': ['现代控制理论A', '现代控制理论'],
            '电力电子': ['电力电子技术A', '电力电子技术B', '电力电子技术'],
            '计控': ['计算机控制技术A', '计算机控制技术'],
            'AI': ['人工智能原理', '人工智能原理及应用', '人工智能概论'],
            '机器学习': ['机器学习'],
            '深度学习': ['深度学习应用'],
            '图像处理': ['图像处理与视频分析A', '图像处理与视频分析'],
            '数据挖掘': ['数据挖掘'],
            '知识图谱': ['知识图谱A', '知识图谱'],
            '操作系统': ['操作系统A'],
            '数据库': ['数据库技术'],
            '算法': ['算法设计与分析', '算法导论'],
            '嵌入式': ['嵌入式系统', '嵌入式系统B', '嵌入式视音频系统开发', '嵌入式人工智能技术'],
            '通信原理': ['通信原理A', '通信原理'],
            '信号': ['信号与系统A', '信号与系统', '数字信号处理'],
        }
    
    def retrieve_relevant_knowledge(self, question: str, top_k: int = 10) -> List[Dict[str, Any]]:
        keywords = self._extract_keywords(question)
        
        # 为每个关键词分配配额，确保所有关键词都有贡献
        per_keyword_quota = max(5, top_k // len(keywords)) if keywords else top_k
        
        all_triples = []
        seen = set()
        
        # 第一轮：每个关键词贡献一定数量的三元组
        for keyword in keywords:
            triples = self.kg.fuzzy_search(keyword)
            count = 0
            for triple in triples:
                key = (triple['subject'], triple['relation'], triple['object'])
                if key not in seen:
                    seen.add(key)
                    all_triples.append(triple)
                    count += 1
                    if count >= per_keyword_quota:
                        break
        
        # 第二轮：如果还没达到top_k，继续添加剩余的三元组
        if len(all_triples) < top_k:
            for keyword in keywords:
                triples = self.kg.fuzzy_search(keyword)
                for triple in triples:
                    key = (triple['subject'], triple['relation'], triple['object'])
                    if key not in seen:
                        seen.add(key)
                        all_triples.append(triple)
                        if len(all_triples) >= top_k:
                            break
                if len(all_triples) >= top_k:
                    break
        
        return all_triples[:top_k]
    
    def _extract_keywords(self, question: str) -> List[str]:
        import re
        
        keywords = []
        
        # 1. 先检查别名映射（专业和课程简称）
        for alias, full_names in self.course_aliases.items():
            if alias in question:
                keywords.extend(full_names)
                if len(keywords) >= 5:
                    break
        
        # 2. 提取重要的关键模式词（如"双语"、"学分"等）- 优先级高
        keywords_patterns = ['双语教学', '双语', '学分', '学期', '开设', '培养', 
                            '专业', '课程', '能力', '方向', '前置', '先修', 
                            '属于', '要求', '介绍', '详情', '信息', '学院']
        
        for pattern in keywords_patterns:
            if pattern in question and pattern not in keywords:
                keywords.append(pattern)
        
        # 3. 从知识图谱中动态获取所有实体（主体和客体）
        all_subjects = self.kg.get_all_subjects()
        all_objects = self.kg.get_all_objects()
        all_entities = set(all_subjects + all_objects)
        
        # 按长度排序，优先匹配长实体（避免"机器学习"被拆成"机器"和"学习"）
        sorted_entities = sorted(all_entities, key=len, reverse=True)
        
        # 匹配知识图谱中的实体
        for entity in sorted_entities:
            if entity in question and entity not in keywords:
                keywords.append(entity)
                if len(keywords) >= 8:  # 最多匹配8个关键词
                    break
        
        # 4. 如果还没有找到足够的关键词，提取所有中英文词
        if len(keywords) < 3:
            words = re.findall(r'[\u4e00-\u9fa5A-Za-z0-9]+', question)
            for word in words:
                if len(word) >= 2 and word not in keywords:
                    keywords.append(word)
                    if len(keywords) >= 8:
                        break
        
        return keywords[:10]  # 返回最多10个关键词
    
    def format_knowledge_context(self, triples: List[Dict[str, Any]]) -> str:
        if not triples:
            return "暂无相关知识。"
        
        context = "相关知识：\n"
        for i, triple in enumerate(triples, 1):
            context += f"{i}. {triple['subject']}（{triple['subject_type']}）"
            context += f"{triple['relation']}"
            context += f"{triple['object']}（{triple['object_type']}）\n"
        
        return context
