import os
import json
import logging
from flask import Flask, render_template, request, jsonify
import math
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
    """Calculate cosine similarity between two vectors using pure Python"""
    # Guard against empty vectors
    if not a or not b:
        return 0.0
    # Compute dot product and norms
    dot = 0.0
    norm_a = 0.0
    norm_b = 0.0
    # Assume equal length embeddings
    for x, y in zip(a, b):
        dot += x * y
        norm_a += x * x
        norm_b += y * y
    denom = math.sqrt(norm_a) * math.sqrt(norm_b)
    if denom == 0:
        return 0.0
    return dot / denom

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
    feature_toolbar = os.environ.get("FEATURE_TOOLBAR", "0") == "1"
    return render_template('index.html', total_docs=len(knowledge_base), feature_toolbar=feature_toolbar)

@app.route('/tags')
def list_tags():
    """Return top tags. If q provided, rank tags by similarity-weighted score; else by overall count.
    Query params: q (optional), limit (default 5)
    """
    try:
        limit = max(1, min(20, int(request.args.get('limit', 5))))
    except ValueError:
        limit = 5
    q = (request.args.get('q') or '').strip()

    # If no knowledge
    if not knowledge_base:
        return jsonify([])

    if not q:
        # Overall top by count
        counts = {}
        for item in knowledge_base:
            for t in item.get('tags', []) or []:
                if isinstance(t, str):
                    key = t.strip().lower()
                    if not key:
                        continue
                    counts[key] = counts.get(key, 0) + 1
        ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
        return jsonify([{"tag": k, "count": v} for k, v in ranked[:limit]])

    # Query present: compute best-chunk similarity per doc and weight tag scores
    try:
        qe = get_query_embedding_cached(q)
    except Exception:
        qe = None

    scores = {}
    if qe is not None:
        for item in knowledge_base:
            best_sim = 0.0
            if 'chunks' in item and item['chunks']:
                for ch in item['chunks']:
                    emb = ch.get('embedding') or []
                    s = cosine_similarity(qe, emb)
                    if s > best_sim:
                        best_sim = s
            elif 'embedding' in item:
                best_sim = cosine_similarity(qe, item.get('embedding') or [])
            if best_sim > 0:
                for t in item.get('tags', []) or []:
                    if isinstance(t, str) and t.strip():
                        key = t.strip().lower()
                        scores[key] = scores.get(key, 0.0) + float(best_sim)

    # Fallback: if no scores (e.g., qe None), use counts
    if not scores:
        counts = {}
        for item in knowledge_base:
            for t in item.get('tags', []) or []:
                if isinstance(t, str):
                    key = t.strip()
                    if not key:
                        continue
                    counts[key] = counts.get(key, 0) + 1
        ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
        return jsonify([{"tag": k, "count": v} for k, v in ranked[:limit]])

    ranked = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
    return jsonify([{"tag": k, "score": v} for k, v in ranked[:limit]])

@app.route('/search')
@limiter.limit("60/minute")
def search():
    """Search endpoint"""
    query = request.args.get('q', '').strip()
    # Optional filters
    raw_tags = request.args.get('tags', '').strip()
    req_tags = [t.lower() for t in raw_tags.split(',') if t.strip()]
    sort = request.args.get('sort', 'relevance').lower()
    try:
        limit = max(1, min(50, int(request.args.get('limit', 20))))
        offset = max(0, int(request.args.get('offset', 0)))
    except ValueError:
        limit, offset = 20, 0
    # Allow tag-only searches: only return empty if neither query nor tags
    if (not query and not req_tags) or not knowledge_base:
        return jsonify({"total": 0, "results": []})
    
    try:
        cache_key = f"{query}|{limit}|{offset}|{','.join(req_tags)}|{sort}"
        if cache_key in results_cache:
            return jsonify(results_cache[cache_key])

        query_embedding = get_query_embedding_cached(query) if query else None

        # Calculate one score per document (best matching chunk)
        scored = []
        for item in knowledge_base:
            best_sim = -1.0
            best_snippet = ''
            best_chunk_index = 0

            if 'chunks' in item and item['chunks']:
                for idx, ch in enumerate(item['chunks']):
                    sim = cosine_similarity(query_embedding, ch.get('embedding') or []) if query_embedding is not None else 0.0
                    if sim > best_sim:
                        best_sim = sim
                        text = ch.get('text', '')
                        best_snippet = text[:240] + ('...' if len(text) > 240 else '')
                        best_chunk_index = idx
            elif 'embedding' in item:
                best_sim = cosine_similarity(query_embedding, item.get('embedding') or []) if query_embedding is not None else 0.0
                text = item.get('content', '')
                best_snippet = text[:240] + ('...' if len(text) > 240 else '')

            # If no query, include the document (tag filtering happens below)
            if query_embedding is None or best_sim > 0.1:
                # Timestamps from build (fallback to filesystem)
                try:
                    fs_mtime = os.path.getmtime(os.path.join('knowledge', item['file']))
                    fs_ctime = os.path.getctime(os.path.join('knowledge', item['file']))
                except Exception:
                    fs_mtime = 0
                    fs_ctime = 0
                scored.append({
                    'title': item['title'],
                    'snippet': best_snippet,
                    'similarity': float(best_sim),
                    'file': item['file'],
                    'chunk_index': best_chunk_index,
                    'tags': [t.strip().lower() for t in (item.get('tags', []) or []) if isinstance(t, str) and t.strip()],
                    'created_ts': float(item.get('created_ts') or fs_ctime or 0),
                    'modified_ts': float(item.get('modified_ts') or fs_mtime or 0)
                })

        # Optional tag filtering (AND semantics)
        if req_tags:
            def has_all_tags(r):
                item_tags = {t.lower() for t in (r.get('tags') or [])}
                return all(t in item_tags for t in req_tags)
            scored = [r for r in scored if has_all_tags(r)]

        # Optional sorting using timestamps from build (fallback to fs mtime)
        if sort in ('newest', 'oldest'):
            if sort == 'newest':
                scored.sort(key=lambda x: x.get('modified_ts', 0), reverse=True)
            else:  # oldest
                # Prefer created_ts; fallback to modified_ts
                scored.sort(key=lambda x: (x.get('created_ts') or x.get('modified_ts') or 0))
        else:
            # Default: relevance
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
