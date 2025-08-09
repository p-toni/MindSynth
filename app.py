import os
import json
import logging
from flask import Flask, render_template, request, jsonify
import numpy as np
from openai import OpenAI
import markdown

# Configure logging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-key-change-in-production")

# Initialize OpenAI client
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "your-openai-api-key")
openai_client = OpenAI(api_key=OPENAI_API_KEY)

# Load embeddings
try:
    with open('embeddings.json', 'r', encoding='utf-8') as f:
        knowledge_base = json.load(f)
    logging.info(f"Loaded {len(knowledge_base)} knowledge entries")
except FileNotFoundError:
    knowledge_base = []
    logging.warning("No embeddings.json found. Run build.py to generate embeddings.")

def cosine_similarity(a, b):
    """Calculate cosine similarity between two vectors"""
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

def get_embedding(text):
    """Get embedding for text using OpenAI"""
    response = openai_client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return response.data[0].embedding

@app.route('/')
def index():
    """Main page"""
    return render_template('index.html', total_docs=len(knowledge_base))

@app.route('/search')
def search():
    """Search endpoint"""
    query = request.args.get('q', '').strip()
    if not query or not knowledge_base:
        return jsonify([])
    
    try:
        # Get query embedding
        query_embedding = get_embedding(query)
        
        # Calculate similarities
        results = []
        for item in knowledge_base:
            similarity = cosine_similarity(query_embedding, item['embedding'])
            if similarity > 0.3:  # Threshold for relevance
                results.append({
                    'title': item['title'],
                    'content': item['content'][:300] + ('...' if len(item['content']) > 300 else ''),
                    'similarity': float(similarity),
                    'file': item['file']
                })
        
        # Sort by similarity and return top 5
        results.sort(key=lambda x: x['similarity'], reverse=True)
        return jsonify(results[:5])
        
    except Exception as e:
        logging.error(f"Search error: {e}")
        return jsonify([]), 500

@app.route('/content/<path:filename>')
def get_content(filename):
    """Get full content of a knowledge file"""
    for item in knowledge_base:
        if item['file'] == filename:
            html_content = markdown.markdown(item['content'])
            return jsonify({
                'title': item['title'],
                'content': html_content,
                'file': filename
            })
    return jsonify({'error': 'Content not found'}), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
