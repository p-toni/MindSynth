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

def compute_tags(q: str, limit: int):
    """Compute tag rankings based on optional query."""
    if not knowledge_base:
        return []
    if not q:
        counts = {}
        for item in knowledge_base:
            for t in item.get('tags', []) or []:
                if isinstance(t, str):
                    key = t.strip().lower()
                    if not key:
                        continue
                    counts[key] = counts.get(key, 0) + 1
        ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
        return [{"tag": k, "count": v} for k, v in ranked[:limit]]

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

    if not scores:
        counts = {}
        for item in knowledge_base:
            for t in item.get('tags', []) or []:
                if isinstance(t, str):
                    key = t.strip().lower()
                    if not key:
                        continue
                    counts[key] = counts.get(key, 0) + 1
        ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
        return [{"tag": k, "count": v} for k, v in ranked[:limit]]

    ranked = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
    return [{"tag": k, "score": v} for k, v in ranked[:limit]]

def perform_search(query: str, req_tags, sort: str, limit: int, offset: int):
    """Core search implementation reused by desktop and mobile endpoints."""
    if (not query and not req_tags) or not knowledge_base:
        return {"total": 0, "results": []}

    cache_key = f"{query}|{limit}|{offset}|{','.join(req_tags)}|{sort}"
    if cache_key in results_cache:
        return results_cache[cache_key]

    query_embedding = get_query_embedding_cached(query) if query else None

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

        if query_embedding is None or best_sim > 0.1:
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

    if req_tags:
        def has_all_tags(r):
            item_tags = {t.lower() for t in (r.get('tags') or [])}
            return all(t in item_tags for t in req_tags)
        scored = [r for r in scored if has_all_tags(r)]

    if sort in ('newest', 'oldest'):
        if sort == 'newest':
            scored.sort(key=lambda x: x.get('modified_ts', 0), reverse=True)
        else:
            scored.sort(key=lambda x: (x.get('created_ts') or x.get('modified_ts') or 0))
    else:
        scored.sort(key=lambda x: x['similarity'], reverse=True)

    total = len(scored)
    page = scored[offset:offset+limit]
    payload = {"total": total, "results": page}
    results_cache[cache_key] = payload
    return payload

def fetch_content_item(filename: str):
    """Retrieve and sanitize content for a knowledge file."""
    for item in knowledge_base:
        if item['file'] == filename:
            content_to_display = item['content']
            html_content = markdown.markdown(content_to_display)
            tags, attrs = allowed_html()
            html_content = bleach.clean(html_content, tags=tags, attributes=attrs, strip=True)
            return {
                'title': item['title'],
                'content': html_content,
                'file': filename,
                'is_url': item.get('is_url', False),
                'source_url': item.get('source_url'),
                'tags': item.get('tags', [])
            }
    return None
@app.route('/')
def index():
    """Main page"""
    feature_toolbar = os.environ.get("FEATURE_TOOLBAR", "0") == "1"
    ua = request.headers.get('User-Agent', '').lower()
    is_mobile = any(k in ua for k in ['iphone', 'android', 'ipad', 'mobile'])
    return render_template('index.html', total_docs=len(knowledge_base), feature_toolbar=feature_toolbar, is_mobile=is_mobile)

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
    tags = compute_tags(q, limit)
    return jsonify(tags)

@app.route('/mobile/tags')
def mobile_tags():
    """Mobile-optimized tag endpoint with smaller limits."""
    try:
        limit = max(1, min(6, int(request.args.get('limit', 5))))
    except ValueError:
        limit = 5
    q = (request.args.get('q') or '').strip()
    tags = compute_tags(q, limit)
    return jsonify(tags)

@app.route('/search')
@limiter.limit("60/minute")
def search():
    """Search endpoint"""
    query = request.args.get('q', '').strip()
    raw_tags = request.args.get('tags', '').strip()
    req_tags = [t.lower() for t in raw_tags.split(',') if t.strip()]
    sort = request.args.get('sort', 'relevance').lower()
    try:
        limit = max(1, min(50, int(request.args.get('limit', 20))))
        offset = max(0, int(request.args.get('offset', 0)))
    except ValueError:
        limit, offset = 20, 0
    try:
        payload = perform_search(query, req_tags, sort, limit, offset)
        return jsonify(payload)
    except Exception as e:
        logging.error(f"Search error: {e}")
        return jsonify({"total": 0, "results": []}), 500

@app.route('/mobile/search')
def mobile_search():
    """Mobile-optimized search endpoint with reduced limits and payload."""
    query = request.args.get('q', '').strip()
    raw_tags = request.args.get('tags', '').strip()
    req_tags = [t.lower() for t in raw_tags.split(',') if t.strip()]
    sort = request.args.get('sort', 'relevance').lower()
    try:
        limit = max(1, min(15, int(request.args.get('limit', 12))))
        offset = max(0, int(request.args.get('offset', 0)))
    except ValueError:
        limit, offset = 12, 0
    payload = perform_search(query, req_tags, sort, limit, offset)
    simplified = []
    for r in payload.get('results', []):
        simplified.append({
            'title': r.get('title'),
            'snippet': r.get('snippet', '')[:120] + ('...' if len(r.get('snippet', '')) > 120 else ''),
            'similarity': r.get('similarity'),
            'file': r.get('file'),
            'tags': (r.get('tags') or [])[:3]
        })
    return jsonify({'total': payload.get('total', 0), 'results': simplified})

@app.route('/content/<path:filename>')
def get_content(filename):
    """Get full content of a knowledge file"""
    item = fetch_content_item(filename)
    if item:
        return jsonify(item)
    return jsonify({'error': 'Content not found'}), 404

@app.route('/mobile/content/<path:filename>')
def mobile_content(filename):
    """Simplified content endpoint for mobile sheets"""
    item = fetch_content_item(filename)
    if item:
        simplified = {
            'title': item['title'],
            'content': item['content'],
            'tags': (item.get('tags') or [])[:6]
        }
        return jsonify(simplified)
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
