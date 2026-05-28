import asyncio
import hashlib
import inspect
import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from memory_store import MemoryStore

try:
    from graphiti_core.cross_encoder.client import CrossEncoderClient
    from graphiti_core.embedder.client import EmbedderClient
except Exception:
    CrossEncoderClient = object
    EmbedderClient = object


class HashEmbedder(EmbedderClient):
    def __init__(self, dimensions: int = 1024):
        self.dimensions = dimensions

    async def create(self, input_data) -> List[float]:
        if not isinstance(input_data, str):
            input_data = " ".join(str(item) for item in input_data)
        vector = [0.0] * self.dimensions
        tokens = input_data.lower().split() or [input_data.lower()]
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimensions
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign
        norm = sum(value * value for value in vector) ** 0.5 or 1.0
        return [value / norm for value in vector]

    async def create_batch(self, input_data_list: List[str]) -> List[List[float]]:
        return [await self.create(item) for item in input_data_list]


class DashScopeEmbedder(EmbedderClient):
    def __init__(self, api_key: str, model: str = "text-embedding-v3"):
        self.api_key = api_key
        self.model = model
        self.fallback_embedder = HashEmbedder()

    async def create(self, input_data) -> List[float]:
        vectors = await self.create_batch([input_data if isinstance(input_data, str) else str(input_data)])
        return vectors[0]

    async def create_batch(self, input_data_list: List[str]) -> List[List[float]]:
        import dashscope
        from http import HTTPStatus

        dashscope.api_key = self.api_key
        vectors = []
        for start in range(0, len(input_data_list), 10):
            batch = input_data_list[start:start + 10]
            response = None
            last_error = None
            for attempt in range(3):
                try:
                    response = dashscope.TextEmbedding.call(
                        model=self.model,
                        input=batch,
                    )
                    break
                except Exception as exc:
                    last_error = exc
                    if attempt == 2:
                        vectors.extend(await self.fallback_embedder.create_batch(batch))
                        response = None
                        break
                    time.sleep(1 + attempt)
            if response is None:
                continue

            status_code = getattr(response, "status_code", None)
            if status_code is not None and status_code != HTTPStatus.OK:
                message = getattr(response, "message", response)
                raise RuntimeError(f"DashScope embedding failed: {message}")

            output = getattr(response, "output", None) or response.get("output", {})
            embeddings = getattr(output, "embeddings", None) or output.get("embeddings", [])
            embeddings = sorted(embeddings, key=lambda item: item.get("text_index", 0))
            vectors.extend(item["embedding"] for item in embeddings)
        return vectors


class SimpleCrossEncoder(CrossEncoderClient):
    async def rank(self, query: str, passages: List[str]) -> List[tuple[str, float]]:
        query_terms = set(query.lower().split())
        ranked = []
        for passage in passages:
            passage_terms = set(passage.lower().split())
            score = float(len(query_terms & passage_terms))
            ranked.append((passage, score))
        return sorted(ranked, key=lambda item: item[1], reverse=True)


class GraphitiMemoryStore:
    """Synchronous adapter around Graphiti's async memory graph API.

    The chatbot code is synchronous, while graphiti-core exposes async methods.
    This adapter keeps the existing memory-store surface small and adds a local
    JSON fallback so the app can still run before Neo4j/Graphiti is configured.
    """

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        fallback_file: Optional[str] = None,
    ):
        self.config = config or {}
        self.enabled = bool(self.config.get("enabled", True))
        self.group_id = self.config.get("group_id") or os.getenv("GRAPHITI_GROUP_ID", "student_default")
        self.search_limit = int(self.config.get("search_limit", 8))
        self.fallback = MemoryStore(fallback_file)
        self.graphiti = None
        self.episode_type = None
        self.loop = asyncio.new_event_loop()
        self.initialized = False
        self.status = "not_initialized"
        self.last_error = ""
        self.recent_facts: List[str] = []

        if self.enabled:
            self._initialize()
        else:
            self.status = "disabled"

    def _initialize(self):
        try:
            from graphiti_core import Graphiti
            from graphiti_core.nodes import EpisodeType
        except Exception as exc:
            self.status = "fallback"
            self.last_error = f"graphiti-core is not available: {exc}"
            return

        self._patch_neo4j_520_dynamic_labels()

        neo4j_uri = self.config.get("neo4j_uri") or os.getenv("NEO4J_URI")
        neo4j_user = self.config.get("neo4j_user") or os.getenv("NEO4J_USER", "neo4j")
        neo4j_password = self.config.get("neo4j_password") or os.getenv("NEO4J_PASSWORD")

        if not neo4j_uri or not neo4j_password:
            self.status = "fallback"
            self.last_error = "NEO4J_URI and NEO4J_PASSWORD are required for Graphiti."
            return

        try:
            llm_client = self._build_llm_client()
            embedder = self._build_embedder()
            cross_encoder = SimpleCrossEncoder()
            self.graphiti = Graphiti(
                neo4j_uri,
                neo4j_user,
                neo4j_password,
                llm_client=llm_client,
                embedder=embedder,
                cross_encoder=cross_encoder,
            )
            self.episode_type = EpisodeType
            self._await_if_needed(self.graphiti.build_indices_and_constraints())
            self.initialized = True
            self.status = "graphiti"
            self.last_error = ""
        except Exception as exc:
            self.graphiti = None
            self.status = "fallback"
            self.last_error = f"Graphiti initialization failed: {exc}"

    def _patch_neo4j_520_dynamic_labels(self):
        try:
            from graphiti_core.models.nodes import node_db_queries
        except Exception:
            return

        if getattr(node_db_queries, "_zjut_neo4j_520_patch", False):
            return

        original = node_db_queries.get_entity_node_save_query

        def patched_get_entity_node_save_query(provider):
            query = original(provider)
            return query.replace("                SET n:$(node.labels)\n", "")

        node_db_queries.get_entity_node_save_query = patched_get_entity_node_save_query
        node_db_queries._zjut_neo4j_520_patch = True

    def _build_llm_client(self):
        api_key = (
            self.config.get("llm_api_key")
            or os.getenv("GRAPHITI_LLM_API_KEY")
            or os.getenv("OPENAI_API_KEY")
        )
        model = self.config.get("llm_model") or os.getenv("GRAPHITI_LLM_MODEL")
        base_url = self.config.get("llm_base_url") or os.getenv("GRAPHITI_LLM_BASE_URL")
        if not api_key:
            return None

        from graphiti_core.llm_client.config import LLMConfig
        from graphiti_core.llm_client.openai_generic_client import OpenAIGenericClient

        return OpenAIGenericClient(
            config=LLMConfig(api_key=api_key, model=model, base_url=base_url)
        )

    def _build_embedder(self):
        if self.config.get("embedding_provider") == "dashscope":
            api_key = self.config.get("embedding_api_key") or os.getenv("DASHSCOPE_API_KEY")
            if not api_key:
                raise ValueError("DASHSCOPE_API_KEY or memory.embedding_api_key is required.")
            return DashScopeEmbedder(
                api_key=api_key,
                model=self.config.get("embedding_model", "text-embedding-v3"),
            )
        if self.config.get("embedding_provider") == "openai":
            from graphiti_core.embedder.openai import OpenAIEmbedder, OpenAIEmbedderConfig

            return OpenAIEmbedder(
                config=OpenAIEmbedderConfig(
                    api_key=self.config.get("embedding_api_key") or os.getenv("OPENAI_API_KEY"),
                    base_url=self.config.get("embedding_base_url"),
                    embedding_model=self.config.get("embedding_model", "text-embedding-3-small"),
                    embedding_dim=int(self.config.get("embedding_dim", 1024)),
                )
            )
        return HashEmbedder(int(self.config.get("embedding_dim", 1024)))

    def get(self) -> Dict[str, Any]:
        fallback_snapshot = self.fallback.get()
        return {
            "backend": self.status,
            "group_id": self.group_id,
            "recent_facts": self.recent_facts,
            "fallback_memory": fallback_snapshot,
            "last_error": self.last_error,
            "updated_at": fallback_snapshot.get("updated_at", ""),
        }

    def clear(self) -> Dict[str, Any]:
        self.recent_facts = []
        self.fallback.clear()
        if self.initialized:
            # Graphiti does not expose a stable group-scoped clear in all versions.
            # Rotate the namespace so new chats start with an empty memory context.
            self.group_id = f"{self.group_id}_cleared_{int(time.time())}"
        return self.get()

    def format_for_prompt(self, question: str = "") -> str:
        facts = self.search(question, self.search_limit) if question else self.recent_facts[-self.search_limit:]
        if facts:
            return "学生长期记忆(Graphiti)：\n" + "\n".join(f"- {fact}" for fact in facts)

        fallback_context = self.fallback.format_for_prompt()
        if self.status == "graphiti":
            return "学生长期记忆(Graphiti)：暂无。"
        return f"{fallback_context}\n\n[Graphiti状态] {self.last_error}"

    def search(self, query: str, top_k: int = 8) -> List[str]:
        if not self.initialized or not query:
            return self.recent_facts[-top_k:]

        try:
            results = self._run(self._search_async(query, top_k))
            facts = [fact for fact in results if fact]
            self.recent_facts = self._dedupe((self.recent_facts + facts)[-30:])
            return facts[:top_k]
        except Exception as exc:
            self.status = "fallback"
            self.last_error = f"Graphiti search failed: {exc}"
            return self.recent_facts[-top_k:]

    def add_interaction(self, question: str, answer: str):
        self.fallback.apply_extraction(question, {})
        if not self.initialized or not question:
            return

        episode_body = f"Student: {question}\nAssistant: {answer}"
        episode_name = f"zjut_chat_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"

        try:
            self._run(
                self.graphiti.add_episode(
                    name=episode_name,
                    episode_body=episode_body,
                    source=self.episode_type.message,
                    source_description="ZJUT learning assistant conversation",
                    reference_time=datetime.now(),
                    group_id=self.group_id,
                )
            )
            if question not in self.recent_facts:
                self.recent_facts.append(f"学生曾询问：{question}")
                self.recent_facts = self.recent_facts[-30:]
        except Exception as exc:
            self.status = "fallback"
            self.last_error = f"Graphiti add_episode failed: {exc}"

    async def _search_async(self, query: str, top_k: int) -> List[str]:
        try:
            results = await self.graphiti.search(query=query, group_ids=[self.group_id], num_results=top_k)
        except TypeError:
            try:
                results = await self.graphiti.search(query=query, group_id=self.group_id)
            except TypeError:
                results = await self.graphiti.search(query=query)

        if hasattr(results, "edges"):
            results = results.edges
        elif hasattr(results, "results"):
            results = results.results

        facts = []
        for item in results[:top_k]:
            facts.append(self._result_to_text(item))
        return facts

    def _result_to_text(self, item: Any) -> str:
        for attr in ("fact", "summary", "name", "content"):
            value = getattr(item, attr, None)
            if value:
                return str(value)
        if isinstance(item, dict):
            for key in ("fact", "summary", "name", "content"):
                if item.get(key):
                    return str(item[key])
        return str(item)

    def _run(self, coro):
        return self.loop.run_until_complete(coro)

    def _await_if_needed(self, value):
        if inspect.isawaitable(value):
            return self._run(value)
        return value

    def _dedupe(self, values: List[str]) -> List[str]:
        seen = set()
        output = []
        for value in values:
            if value and value not in seen:
                seen.add(value)
                output.append(value)
        return output
