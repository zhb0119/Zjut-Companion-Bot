import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from chatbot import ChatBot

def test_bot():
    print("开始测试问答机器人...\n")
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    triple_file = os.path.join(current_dir, 'data/zjut_triples_manual.json')
    
    bot = ChatBot(triple_file)
    
    test_questions = [
        "自动化专业开设了哪些课程？",
        "自动化专业需要多少学分？",
        "自动控制原理的前置课程是什么？",
        "自动化专业培养什么能力？",
        "自动化专业适用于什么方向？",
        "介绍一下自动化专业",
    ]
    
    print("\n" + "="*60)
    print("开始测试问答功能")
    print("="*60 + "\n")
    
    for i, question in enumerate(test_questions, 1):
        print(f"\n【测试 {i}】")
        print(f"问题: {question}")
        print("-" * 60)
        answer = bot.ask(question)
        print(f"回答:\n{answer}")
        print("="*60)
    
    print("\n[OK] 测试完成！")

if __name__ == "__main__":
    test_bot()
