from knowledge_graph import KnowledgeGraph
from question_parser import QuestionParser
from answer_generator import AnswerGenerator


class ChatBot:
    def __init__(self, triple_file: str):
        self.kg = KnowledgeGraph(triple_file)
        self.parser = QuestionParser()
        self.answer_gen = AnswerGenerator(self.kg)
        
        print("=" * 60)
        print("浙江工业大学自动化专业问答机器人")
        print("=" * 60)
        print(f"知识库加载完成！共有 {len(self.kg.triples)} 条知识三元组。")
        print("=" * 60)
    
    def ask(self, question: str) -> str:
        if not question or not question.strip():
            return "请输入有效的问题。"
        
        parsed = self.parser.parse(question)
        answer = self.answer_gen.generate(parsed)
        
        return answer
    
    def run(self):
        print("\n您可以问我关于自动化专业的问题，例如：")
        print("  - 自动化专业开设了哪些课程？")
        print("  - 自动化专业需要多少学分？")
        print("  - 自动控制原理的前置课程是什么？")
        print("  - 自动化专业培养什么能力？")
        print("  - 介绍一下自动化专业")
        print("\n输入 'quit' 或 'exit' 退出程序。")
        print("=" * 60)
        
        while True:
            try:
                question = input("\n请输入您的问题: ").strip()
                
                if question.lower() in ['quit', 'exit', '退出', 'q']:
                    print("\n感谢使用！再见！")
                    break
                
                if not question:
                    continue
                
                answer = self.ask(question)
                print(f"\n回答：\n{answer}")
                print("-" * 60)
                
            except KeyboardInterrupt:
                print("\n\n感谢使用！再见！")
                break
            except Exception as e:
                print(f"\n发生错误: {str(e)}")
                print("请重新输入问题。")


if __name__ == "__main__":
    import os
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    triple_file = os.path.join(current_dir, '../data/zjut_triples_manual.json')
    
    bot = ChatBot(triple_file)
    bot.run()
