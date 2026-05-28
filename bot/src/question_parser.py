import re
from typing import Dict, List, Optional, Tuple


class QuestionParser:
    def __init__(self):
        self.question_patterns = {
            'course_list': [
                r'(.+?)开设了?(哪些|什么)课程',
                r'(.+?)有(哪些|什么)课程',
                r'(.+?)的课程有(哪些|什么)',
            ],
            'belong_to': [
                r'(.+?)属于(哪个|什么)(学院|专业|类别)',
                r'(.+?)是(哪个|什么)(学院|专业|类别)的',
            ],
            'credit_requirement': [
                r'(.+?)需要多少学分',
                r'(.+?)要求多少学分',
                r'(.+?)(的)?学分(要求|是多少)',
            ],
            'prerequisite': [
                r'(.+?)的前置课程是(什么|哪些)',
                r'学(.+?)需要先学(什么|哪些)',
                r'(.+?)的先修课程',
            ],
            'capability': [
                r'(.+?)培养(什么|哪些)能力',
                r'(.+?)(的)?能力培养',
            ],
            'career_direction': [
                r'(.+?)适用于(什么|哪些)(方向|领域)',
                r'(.+?)的就业方向',
                r'(.+?)可以从事(什么|哪些)工作',
            ],
            'course_category': [
                r'(.+?)是什么类型的课程',
                r'(.+?)属于什么课程',
            ],
            'major_info': [
                r'(.+?)(专业|学院)的?(主干学科|核心课程)',
                r'介绍一下(.+?)(专业|学院)',
            ],
            'reverse_belong': [
                r'(哪些|什么)课程属于(.+)',
                r'(.+?)(方向|类别)有(哪些|什么)课程',
            ],
        }
        
        self.relation_mapping = {
            'course_list': '开设',
            'belong_to': '属于',
            'credit_requirement': '要求',
            'prerequisite': '前置课程',
            'capability': '培养',
            'career_direction': '适用于',
            'course_category': '属于',
            'major_info': '包含',
            'reverse_belong': '属于',
        }
    
    def parse(self, question: str) -> Dict[str, any]:
        question = question.strip()
        
        for intent, patterns in self.question_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, question)
                if match:
                    entity = match.group(1).strip()
                    return {
                        'intent': intent,
                        'entity': entity,
                        'relation': self.relation_mapping.get(intent),
                        'original_question': question
                    }
        
        return {
            'intent': 'unknown',
            'entity': None,
            'relation': None,
            'original_question': question
        }
    
    def extract_keywords(self, question: str) -> List[str]:
        keywords = []
        
        important_words = ['专业', '课程', '学院', '学分', '能力', '方向', '前置', '先修']
        for word in important_words:
            if word in question:
                keywords.append(word)
        
        entities = re.findall(r'[\u4e00-\u9fa5A-Za-z0-9]+', question)
        keywords.extend([e for e in entities if len(e) > 1])
        
        return list(set(keywords))
