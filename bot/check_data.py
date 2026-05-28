import json

with open('data/zjut_triples_manual.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
    triples = data['triple_list']
    
print(f"三元组总数: {len(triples)}")

# 统计实体
subjects = set([t['subject'] for t in triples])
objects = set([t['object'] for t in triples])
all_entities = subjects | objects

print(f"\n实体统计:")
print(f"  总实体数: {len(all_entities)}")
print(f"  主体数: {len(subjects)}")
print(f"  客体数: {len(objects)}")

# 按类型统计
entity_types = {}
for t in triples:
    s_type = t['subject_type']
    o_type = t['object_type']
    entity_types[s_type] = entity_types.get(s_type, set())
    entity_types[o_type] = entity_types.get(o_type, set())
    entity_types[s_type].add(t['subject'])
    entity_types[o_type].add(t['object'])

print(f"\n按类型统计:")
for etype, entities in sorted(entity_types.items()):
    print(f"  {etype}: {len(entities)}个")

# 关系统计
relations = set([t['relation'] for t in triples])
print(f"\n关系类型数: {len(relations)}")
print(f"关系类型: {sorted(relations)}")
