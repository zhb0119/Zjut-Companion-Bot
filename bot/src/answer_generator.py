from typing import List, Dict, Any
from knowledge_graph import KnowledgeGraph


class AnswerGenerator:
    def __init__(self, kg: KnowledgeGraph):
        self.kg = kg
    
    def generate(self, parsed_question: Dict[str, Any]) -> str:
        intent = parsed_question['intent']
        entity = parsed_question['entity']
        
        if intent == 'unknown':
            return self.handle_unknown(parsed_question)
        
        handler_map = {
            'course_list': self.handle_course_list,
            'belong_to': self.handle_belong_to,
            'credit_requirement': self.handle_credit_requirement,
            'prerequisite': self.handle_prerequisite,
            'capability': self.handle_capability,
            'career_direction': self.handle_career_direction,
            'course_category': self.handle_course_category,
            'major_info': self.handle_major_info,
            'reverse_belong': self.handle_reverse_belong,
        }
        
        handler = handler_map.get(intent)
        if handler:
            return handler(entity)
        
        return "抱歉，我无法理解您的问题。"
    
    def handle_course_list(self, entity: str) -> str:
        triples = self.kg.query_by_subject_relation(entity, '开设')
        
        if not triples:
            return f"抱歉，我没有找到关于{entity}开设课程的信息。"
        
        courses = [t['object'] for t in triples]
        answer = f"{entity}开设的课程有：\n"
        for i, course in enumerate(courses, 1):
            answer += f"{i}. {course}\n"
        
        return answer.strip()
    
    def handle_belong_to(self, entity: str) -> str:
        triples = self.kg.query_by_subject_relation(entity, '属于')
        
        if not triples:
            return f"抱歉，我没有找到关于{entity}所属信息。"
        
        answer = f"{entity}属于：\n"
        for triple in triples:
            answer += f"- {triple['object']}（{triple['object_type']}）\n"
        
        return answer.strip()
    
    def handle_credit_requirement(self, entity: str) -> str:
        triples = self.kg.query_by_subject_relation(entity, '要求')
        
        if not triples:
            return f"抱歉，我没有找到关于{entity}学分要求的信息。"
        
        for triple in triples:
            if '学分' in triple['object']:
                return f"{entity}要求{triple['object']}。"
        
        return f"抱歉，我没有找到关于{entity}学分要求的具体信息。"
    
    def handle_prerequisite(self, entity: str) -> str:
        triples = self.kg.query_by_relation_object('前置课程', entity)
        
        if not triples:
            return f"抱歉，我没有找到{entity}的前置课程信息。"
        
        answer = f"{entity}的前置课程有：\n"
        for i, triple in enumerate(triples, 1):
            answer += f"{i}. {triple['subject']}\n"
        
        return answer.strip()
    
    def handle_capability(self, entity: str) -> str:
        triples = self.kg.query_by_subject_relation(entity, '培养')
        
        if not triples:
            return f"抱歉，我没有找到关于{entity}培养能力的信息。"
        
        answer = f"{entity}培养的能力包括：\n"
        for i, triple in enumerate(triples, 1):
            answer += f"{i}. {triple['object']}\n"
        
        return answer.strip()
    
    def handle_career_direction(self, entity: str) -> str:
        triples = self.kg.query_by_subject_relation(entity, '适用于')
        
        if not triples:
            return f"抱歉，我没有找到关于{entity}职业方向的信息。"
        
        answer = f"{entity}适用于以下方向：\n"
        for i, triple in enumerate(triples, 1):
            answer += f"{i}. {triple['object']}\n"
        
        return answer.strip()
    
    def handle_course_category(self, entity: str) -> str:
        triples = self.kg.query_by_subject_relation(entity, '属于')
        
        if not triples:
            return f"抱歉，我没有找到关于{entity}课程类别的信息。"
        
        for triple in triples:
            if '课程' in triple['object_type']:
                return f"{entity}属于{triple['object']}。"
        
        return f"抱歉，我没有找到关于{entity}课程类别的具体信息。"
    
    def handle_major_info(self, entity: str) -> str:
        all_triples = self.kg.query_by_subject(entity)
        
        if not all_triples:
            return f"抱歉，我没有找到关于{entity}的信息。"
        
        answer = f"关于{entity}的信息：\n\n"
        
        grouped = {}
        for triple in all_triples:
            relation = triple['relation']
            if relation not in grouped:
                grouped[relation] = []
            grouped[relation].append(triple['object'])
        
        relation_names = {
            '属于': '所属',
            '要求': '学分要求',
            '开设': '开设课程',
            '培养': '培养能力',
            '适用于': '适用方向',
            '主干学科': '主干学科',
        }
        
        for relation, objects in grouped.items():
            relation_name = relation_names.get(relation, relation)
            answer += f"【{relation_name}】\n"
            for obj in objects:
                answer += f"  - {obj}\n"
            answer += "\n"
        
        return answer.strip()
    
    def handle_reverse_belong(self, entity: str) -> str:
        triples = self.kg.query_by_relation_object('属于', entity)
        
        if not triples:
            return f"抱歉，我没有找到属于{entity}的课程信息。"
        
        answer = f"属于{entity}的课程有：\n"
        for i, triple in enumerate(triples, 1):
            answer += f"{i}. {triple['subject']}\n"
        
        return answer.strip()
    
    def handle_unknown(self, parsed_question: Dict[str, Any]) -> str:
        question = parsed_question['original_question']
        
        from question_parser import QuestionParser
        parser = QuestionParser()
        keywords = parser.extract_keywords(question)
        
        results = []
        for keyword in keywords:
            results.extend(self.kg.fuzzy_search(keyword))
        
        if not results:
            return "抱歉，我无法理解您的问题，也没有找到相关信息。请尝试换一种方式提问。"
        
        unique_results = []
        seen = set()
        for r in results:
            key = (r['subject'], r['relation'], r['object'])
            if key not in seen:
                seen.add(key)
                unique_results.append(r)
        
        if len(unique_results) > 10:
            unique_results = unique_results[:10]
        
        answer = "我找到了以下相关信息：\n\n"
        for triple in unique_results:
            answer += f"- {triple['subject']} {triple['relation']} {triple['object']}\n"
        
        return answer.strip()
