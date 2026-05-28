import json
from typing import List, Dict, Any, Optional
from collections import defaultdict


class KnowledgeGraph:
    def __init__(self, triple_file: str):
        self.triple_file = triple_file
        self.triples = []
        self.subject_index = defaultdict(list)
        self.object_index = defaultdict(list)
        self.relation_index = defaultdict(list)
        self.load_triples()
        self.build_indexes()
    
    def load_triples(self):
        with open(self.triple_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            self.triples = data.get('triple_list', [])
    
    def build_indexes(self):
        for triple in self.triples:
            subject = triple['subject']
            relation = triple['relation']
            obj = triple['object']
            
            self.subject_index[subject].append(triple)
            self.object_index[obj].append(triple)
            self.relation_index[relation].append(triple)
    
    def query_by_subject(self, subject: str) -> List[Dict[str, Any]]:
        return self.subject_index.get(subject, [])
    
    def query_by_object(self, obj: str) -> List[Dict[str, Any]]:
        return self.object_index.get(obj, [])
    
    def query_by_relation(self, relation: str) -> List[Dict[str, Any]]:
        return self.relation_index.get(relation, [])
    
    def query_by_subject_relation(self, subject: str, relation: str) -> List[Dict[str, Any]]:
        results = []
        for triple in self.subject_index.get(subject, []):
            if triple['relation'] == relation:
                results.append(triple)
        return results
    
    def query_by_relation_object(self, relation: str, obj: str) -> List[Dict[str, Any]]:
        results = []
        for triple in self.relation_index.get(relation, []):
            if triple['object'] == obj:
                results.append(triple)
        return results
    
    def fuzzy_search(self, keyword: str) -> List[Dict[str, Any]]:
        results = []
        for triple in self.triples:
            if (keyword in triple['subject'] or 
                keyword in triple['object'] or 
                keyword in triple['relation']):
                results.append(triple)
        return results
    
    def get_all_subjects(self) -> List[str]:
        return list(self.subject_index.keys())
    
    def get_all_objects(self) -> List[str]:
        return list(self.object_index.keys())
    
    def get_all_relations(self) -> List[str]:
        return list(self.relation_index.keys())
