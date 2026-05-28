from flask import Flask, render_template, request, jsonify
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from chatbot import ChatBot

app = Flask(__name__)

current_dir = os.path.dirname(os.path.abspath(__file__))
triple_file = os.path.join(current_dir, 'data/zjut_triples_manual.json')
bot = ChatBot(triple_file)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/ask', methods=['POST'])
def ask():
    data = request.get_json()
    question = data.get('question', '')
    
    if not question:
        return jsonify({'error': '请输入问题'}), 400
    
    try:
        answer = bot.ask(question)
        return jsonify({'answer': answer})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/stats', methods=['GET'])
def stats():
    return jsonify({
        'total_triples': len(bot.kg.triples),
        'total_subjects': len(bot.kg.get_all_subjects()),
        'total_relations': len(bot.kg.get_all_relations()),
        'total_objects': len(bot.kg.get_all_objects())
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
