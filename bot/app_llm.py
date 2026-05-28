from flask import Flask, jsonify, render_template, request
import os
import sys
import time

sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from llm_chatbot import create_bot_from_config


app = Flask(__name__)

try:
    bot = create_bot_from_config()
    print("LLM 问答机器人启动成功！")
except Exception as exc:
    print(f"警告: 无法加载 LLM 配置: {exc}")
    print("请配置 config.json 文件后重启服务。")
    bot = None


def require_bot():
    if bot is None:
        return jsonify({"error": "机器人未正确配置，请检查 config.json"}), 500
    return None


@app.route("/")
def index():
    return render_template("index_llm.html")


@app.route("/ask", methods=["POST"])
def ask():
    error = require_bot()
    if error:
        return error

    data = request.get_json() or {}
    question = (data.get("question") or "").strip()
    if not question:
        return jsonify({"error": "请输入问题"}), 400

    try:
        start = time.perf_counter()
        print(f"[ask] start question={question[:80]}", flush=True)
        answer = bot.ask(question)
        elapsed = time.perf_counter() - start
        print(f"[ask] done elapsed={elapsed:.2f}s", flush=True)
        return jsonify({"answer": answer})
    except Exception as exc:
        print(f"[ask] failed error={exc}", flush=True)
        return jsonify({"error": str(exc)}), 500


@app.route("/clear", methods=["POST"])
def clear_history():
    error = require_bot()
    if error:
        return error

    try:
        return jsonify({"message": bot.clear_history()})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/memory", methods=["GET"])
def memory():
    error = require_bot()
    if error:
        return error

    try:
        return jsonify(bot.get_memory())
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/memory/clear", methods=["POST"])
def clear_memory():
    error = require_bot()
    if error:
        return error

    try:
        message = bot.clear_memory()
        return jsonify({"message": message, "memory": bot.get_memory()})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/memory/reset", methods=["POST"])
def reset_memory():
    error = require_bot()
    if error:
        return error

    try:
        message = bot.reset_memory()
        return jsonify({"message": message, "memory": bot.get_memory()})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/stats", methods=["GET"])
def stats():
    error = require_bot()
    if error:
        return error

    return jsonify({
        "total_triples": len(bot.kg.triples),
        "total_subjects": len(bot.kg.get_all_subjects()),
        "total_relations": len(bot.kg.get_all_relations()),
        "total_objects": len(bot.kg.get_all_objects()),
        "conversation_length": len(bot.conversation_history),
        "memory_items": sum(
            len(value) for value in bot.get_memory().values() if isinstance(value, list)
        ),
    })


@app.route("/graph")
def graph():
    return render_template("graph.html")


@app.route("/graph/data", methods=["GET"])
def graph_data():
    error = require_bot()
    if error:
        return error

    filter_type = request.args.get("filter", "all")
    limit = int(request.args.get("limit", 100))

    triples = bot.kg.triples
    if filter_type == "major":
        triples = [
            item for item in triples
            if "专业" in item["subject_type"] or "专业" in item["object"]
        ]
    elif filter_type == "course":
        triples = [
            item for item in triples
            if "课程" in item["subject_type"] or "课程" in item["object_type"]
        ]

    triples = triples[:limit]
    nodes = {}
    edges = []

    for triple in triples:
        if triple["subject"] not in nodes:
            nodes[triple["subject"]] = {
                "id": triple["subject"],
                "label": triple["subject"],
                "type": triple["subject_type"],
                "group": triple["subject_type"],
            }

        if triple["object"] not in nodes:
            nodes[triple["object"]] = {
                "id": triple["object"],
                "label": triple["object"],
                "type": triple["object_type"],
                "group": triple["object_type"],
            }

        edges.append({
            "from": triple["subject"],
            "to": triple["object"],
            "label": triple["relation"],
            "title": f"{triple['subject']} {triple['relation']} {triple['object']}",
        })

    return jsonify({"nodes": list(nodes.values()), "edges": edges})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True, use_reloader=False)
