import json
import os
import threading
from typing import Dict, Optional

from graphiti_memory_store import GraphitiMemoryStore
from knowledge_graph import KnowledgeGraph
from llm_client import BaseLLMClient, LLMClientFactory
from rag_retriever import RAGRetriever


class LLMChatBot:
    def __init__(
        self,
        triple_file: str,
        llm_client: BaseLLMClient,
        memory_config: Optional[Dict] = None,
    ):
        self.kg = KnowledgeGraph(triple_file)
        self.retriever = RAGRetriever(self.kg)
        self.llm_client = llm_client
        self.conversation_history = []
        self.memory_store = GraphitiMemoryStore(memory_config)

        self.system_prompt = """你是 ZJUT 伴学 Bot，浙江工业大学信息工程学院的智能学习助手。
你面向自动化、智能科学与技术、通信工程等专业的学生，回答应基于知识图谱和长期记忆。

回答风格：
- 语气友好、简洁、像学长学姐一样给建议。
- 默认不超过 120 字，复杂规划最多 4 条要点。
- 优先使用 Markdown 列表，关键术语用加粗。
- 如果知识库没有相关信息，要明确说明，不编造。

回答原则：
1. 优先使用知识图谱中的课程、学分、培养目标、职业方向等信息。
2. 如果长期记忆与本次问题相关，给出个性化建议。
3. 专业对比问题要覆盖自动化、智能科学与技术、通信工程。
4. 课程规划问题要给出可执行的学习路径。
"""

        print("=" * 60)
        print("ZJUT 伴学 Bot - 智能学习助手")
        print("=" * 60)
        print(f"知识库加载完成，共有 {len(self.kg.triples)} 条知识三元组。")
        print("已启用 LLM + RAG + Memory 问答流程。")
        print("=" * 60)

    def ask(self, question: str, use_history: bool = True) -> str:
        if not question or not question.strip():
            return "请输入有效的问题。"

        relevant_triples = self.retriever.retrieve_relevant_knowledge(question, top_k=50)
        knowledge_context = self.retriever.format_knowledge_context(relevant_triples)
        memory_context = self.memory_store.format_for_prompt(question)

        messages = [{"role": "system", "content": self.system_prompt}]
        if use_history and self.conversation_history:
            messages.extend(self.conversation_history[-6:])

        user_message = f"""用户问题：{question}

{memory_context}

{knowledge_context}

请根据上面的长期记忆和知识图谱信息回答用户问题。
如果知识图谱中没有相关信息，请礼貌说明。
如果长期记忆与本次问题相关，请体现个性化建议；如果无关，不要强行提及。

输出要求：
- 默认不超过 120 字。
- 最多 4 条要点。
- 支持 Markdown。
- 不要重复题目，不要输出原始 HTML。
"""
        messages.append({"role": "user", "content": user_message})

        try:
            answer = self.llm_client.chat(messages, temperature=0.7)
            self.conversation_history.append({"role": "user", "content": question})
            self.conversation_history.append({"role": "assistant", "content": answer})
            self._remember_interaction_async(question, answer)

            if len(self.conversation_history) > 20:
                self.conversation_history = self.conversation_history[-20:]

            return answer
        except Exception as exc:
            return f"调用大语言模型时出错：{exc}\n请检查 API 和配置。"

    def _remember_interaction_async(self, question: str, answer: str):
        def worker():
            try:
                self.memory_store.add_interaction(question, answer)
            except Exception as exc:
                print(f"Graphiti memory write failed: {exc}")

        threading.Thread(target=worker, daemon=True).start()

    def clear_history(self):
        self.conversation_history = []
        return "对话历史已清空。"

    def get_memory(self):
        return self.memory_store.get()

    def clear_memory(self):
        self.memory_store.clear()
        return "学生长期记忆已清空。"

    def reset_memory(self):
        self.memory_store.clear(hard=True)
        self.conversation_history = []
        return "学生长期记忆已从当前 Graphiti 命名空间物理清空。"

    def add_document_memory(self, title: str, content: str):
        self.memory_store.add_document(
            title,
            content,
            source_description="Uploaded transcript or profile document",
        )
        return "文档已写入长期记忆。"

    def run(self):
        print("\n可以询问信息工程学院培养计划相关问题，例如：")
        print("  - 自动化专业开设了哪些课程？")
        print("  - 自动化专业需要多少学分？")
        print("  - 自动控制原理的前置课程是什么？")
        print("  - 我想学习知识图谱，应该先补什么基础？")
        print("\n特殊命令：")
        print("  - memory：查看记忆状态")
        print("  - clear_memory：清空长期记忆命名空间")
        print("  - clear：清空对话历史")
        print("  - quit / exit：退出")
        print("=" * 60)

        while True:
            try:
                question = input("\n请输入问题：").strip()
                if question.lower() in ["quit", "exit", "q", "退出"]:
                    print("\n感谢使用，再见。")
                    break
                if question.lower() in ["clear", "清空"]:
                    print(self.clear_history())
                    continue
                if question.lower() in ["memory", "记忆", "画像"]:
                    print(json.dumps(self.get_memory(), ensure_ascii=False, indent=2))
                    continue
                if question.lower() in ["clear_memory", "清空记忆"]:
                    print(self.clear_memory())
                    continue
                if not question:
                    continue

                print("\n思考中...\n")
                print(f"回答：\n{self.ask(question)}")
                print("-" * 60)
            except KeyboardInterrupt:
                print("\n\n感谢使用，再见。")
                break
            except Exception as exc:
                print(f"\n发生错误：{exc}")


def create_bot_from_config(config_file: str = None) -> LLMChatBot:
    if config_file is None:
        config_file = os.path.join(os.path.dirname(__file__), "../config.json")

    if not os.path.exists(config_file):
        raise FileNotFoundError(
            f"配置文件不存在：{config_file}\n请复制 config.example.json 为 config.json 并填写 API key。"
        )

    with open(config_file, "r", encoding="utf-8") as file:
        config = json.load(file)

    provider = config.get("provider")
    api_config = config.get("api_config", {})
    llm_client = LLMClientFactory.create_client(provider, **api_config)

    current_dir = os.path.dirname(os.path.abspath(__file__))
    triple_file = os.path.join(current_dir, "../data/zjut_triples_manual.json")

    memory_config = dict(config.get("memory", {}))
    if provider in ("deepseek", "openai"):
        memory_config.setdefault("llm_api_key", api_config.get("api_key"))
        memory_config.setdefault(
            "llm_model",
            api_config.get("model", "deepseek-chat" if provider == "deepseek" else "gpt-4o-mini"),
        )
        if provider == "deepseek":
            memory_config.setdefault("llm_base_url", "https://api.deepseek.com")
        else:
            memory_config.setdefault("llm_base_url", api_config.get("base_url"))

    return LLMChatBot(triple_file, llm_client, memory_config=memory_config)


if __name__ == "__main__":
    try:
        bot = create_bot_from_config()
        bot.run()
    except FileNotFoundError as exc:
        print(f"\n错误：{exc}")
    except Exception as exc:
        print(f"\n启动失败：{exc}")
