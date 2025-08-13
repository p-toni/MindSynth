import os
import json
import logging
from flask import Flask, render_template, request, jsonify
import numpy as np
from openai import OpenAI
import markdown
from dotenv import load_dotenv
from cachetools import LRUCache
import bleach
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Configure logging
logging.basicConfig(level=logging.DEBUG)

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-key-change-in-production")

# Rate limiting
limiter = Limiter(get_remote_address, app=app, default_limits=["200 per minute"])  # global cap

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

# Cache for query embeddings and search responses
embedding_cache = LRUCache(maxsize=256)
results_cache = LRUCache(maxsize=128)

def get_query_embedding_cached(query: str):
    if query in embedding_cache:
        return embedding_cache[query]
    emb = get_embedding(query)
    embedding_cache[query] = emb
    return emb

def allowed_html():
    tags = [
        'p','ul','ol','li','strong','em','code','pre','a','blockquote','h1','h2','h3','h4','h5','h6','div','span','br'
    ]
    attrs = {
        'a': ['href','title','target','rel'],
        'blockquote': ['class','data-dnt','data-theme','align'],
        'div': ['class'],
        'span': ['class']
    }
    return tags, attrs

@app.route('/')
def index():
    """Main page"""
    return render_template('index.html', total_docs=len(knowledge_base))

@app.route('/search')
@limiter.limit("60/minute")
def search():
    """Search endpoint"""
    query = request.args.get('q', '').strip()
    try:
        limit = max(1, min(50, int(request.args.get('limit', 20))))
        offset = max(0, int(request.args.get('offset', 0)))
    except ValueError:
        limit, offset = 20, 0
    if not query or not knowledge_base:
        return jsonify({"total": 0, "results": []})
    
    try:
        cache_key = f"{query}|{limit}|{offset}"
        if cache_key in results_cache:
            return jsonify(results_cache[cache_key])

        query_embedding = get_query_embedding_cached(query)

        # Calculate similarities across chunks if present
        scored = []
        for item in knowledge_base:
            if 'chunks' in item and item['chunks']:
                for idx, ch in enumerate(item['chunks']):
                    sim = cosine_similarity(query_embedding, ch['embedding'])
                    if sim > 0.1:
                        snippet = ch.get('text','')[:240]
                        scored.append({
                            'title': item['title'],
                            'snippet': snippet + ('...' if len(ch.get('text',''))>240 else ''),
                            'similarity': float(sim),
                            'file': item['file'],
                            'chunk_index': idx,
                            'tags': item.get('tags', [])
                        })
            elif 'embedding' in item:
                sim = cosine_similarity(query_embedding, item['embedding'])
                if sim > 0.1:
                    scored.append({
                        'title': item['title'],
                        'snippet': item['content'][:240] + ('...' if len(item['content'])>240 else ''),
                        'similarity': float(sim),
                        'file': item['file'],
                        'chunk_index': 0,
                        'tags': item.get('tags', [])
                    })

        scored.sort(key=lambda x: x['similarity'], reverse=True)
        total = len(scored)
        page = scored[offset:offset+limit]
        payload = {"total": total, "results": page}
        results_cache[cache_key] = payload
        return jsonify(payload)
        
    except Exception as e:
        logging.error(f"Search error: {e}")
        return jsonify({"total": 0, "results": []}), 500

@app.route('/content/<path:filename>')
def get_content(filename):
    """Get full content of a knowledge file"""
    for item in knowledge_base:
        if item['file'] == filename:
            content_to_display = item['content']
            
            # For URL-based files, use the content directly without extra formatting
            # The content already includes proper source information
            
            html_content = markdown.markdown(content_to_display)
            tags, attrs = allowed_html()
            html_content = bleach.clean(html_content, tags=tags, attributes=attrs, strip=True)
            return jsonify({
                'title': item['title'],
                'content': html_content,
                'file': filename,
                'is_url': item.get('is_url', False),
                'source_url': item.get('source_url'),
                'tags': item.get('tags', [])
            })
    return jsonify({'error': 'Content not found'}), 404

@app.after_request
def set_security_headers(resp):
    resp.headers['X-Content-Type-Options'] = 'nosniff'
    resp.headers['X-Frame-Options'] = 'DENY'
    resp.headers['Referrer-Policy'] = 'no-referrer-when-downgrade'
    # CSP allowing Twitter widgets to work properly
    csp = "default-src 'self'; script-src 'self' 'unsafe-inline' https://platform.twitter.com https://cdn.syndication.twimg.com; connect-src 'self' https://platform.twitter.com; style-src 'self' 'unsafe-inline' https://platform.twitter.com; img-src 'self' data: https://pbs.twimg.com https://ton.twimg.com https://platform.twitter.com; frame-src https://platform.twitter.com https://syndication.twitter.com; font-src 'self' https://platform.twitter.com;"
    resp.headers['Content-Security-Policy'] = csp
    return resp

if __name__ == '__main__':
    # Use environment PORT for deployment platforms, fallback to 5000
    port = int(os.environ.get('PORT', 5000))
    # Use debug=False in production
    debug = os.environ.get('FLASK_ENV') == 'development'
    app.run(host='0.0.0.0', port=port, debug=debug)
