#!/usr/bin/env python3
"""
Build script to process .md files and generate embeddings
Run this script to update the knowledge base when adding new .md files
"""
import os
import json
import logging
import re
import hashlib
from pathlib import Path
from openai import OpenAI
import trafilatura
import yaml
from urllib.parse import urlparse, quote
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
import html as html_lib
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

# Initialize OpenAI client
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "your-openai-api-key")
openai_client = OpenAI(api_key=OPENAI_API_KEY)

def get_embedding(text):
    """Get embedding for text using OpenAI text-embedding-3-small model"""
    response = openai_client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return response.data[0].embedding

def is_url_only(content):
    """Check if content is just a URL"""
    lines = [line.strip() for line in content.strip().split('\n') if line.strip()]
    if len(lines) == 1:
        url_pattern = r'^https?://[^\s]+$'
        return re.match(url_pattern, lines[0]) is not None
    return False

def _http_get_json(url: str):
    """Minimal JSON fetcher using stdlib to avoid extra deps."""
    try:
        req = Request(url, headers={"User-Agent": "MindSynth/1.0"})
        with urlopen(req, timeout=10) as resp:
            data = resp.read()
            return json.loads(data.decode("utf-8", errors="ignore"))
    except (URLError, HTTPError, TimeoutError, ValueError) as e:
        logging.warning(f"HTTP JSON fetch failed for {url}: {e}")
        return None


def _strip_html(html: str) -> str:
    """Very small HTML-to-text helper for embedding; keeps text only."""
    # Remove script/style blocks
    html = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.I)
    html = re.sub(r"<style[\s\S]*?</style>", " ", html, flags=re.I)
    # Replace <br> and block tags with newlines
    html = re.sub(r"<\s*(br|/p|/div|/li|/h[1-6])\s*>", "\n", html, flags=re.I)
    # Strip remaining tags
    text = re.sub(r"<[^>]+>", " ", html)
    # Unescape entities and collapse whitespace
    text = html_lib.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _twitter_oembed(url: str):
    """Try to fetch Twitter/X oEmbed HTML snippet without auth."""
    # Normalize x.com to twitter.com for the oEmbed endpoint
    parsed = urlparse(url)
    if parsed.netloc.endswith("x.com"):
        url = url.replace(parsed.netloc, "twitter.com")

    oembed_url = (
        "https://publish.twitter.com/oembed?omit_script=true&hide_thread=true&align=center&dnt=true&url="
        + quote(url, safe="")
    )
    data = _http_get_json(oembed_url)
    if data and isinstance(data, dict) and data.get("html"):
        return data["html"], data.get("author_name")
    return None, None


def create_url_preview(url):
    """Create URL preview with embed support for Twitter/X, with text for embedding.
    For regular articles, attempt to fetch and extract main text with trafilatura for embedding quality.
    """
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.replace('www.', '')

        if 'twitter.com' in domain or 'x.com' in domain:
            # Prefer official oEmbed
            embed_html, author = _twitter_oembed(url)
            preview_title = "Tweet Preview" if not author else f"Tweet by {author}"
            if not embed_html:
                # Fallback: basic blockquote linking to the tweet
                embed_html = (
                    f'<blockquote class="twitter-tweet" data-dnt="true" data-theme="light">'
                    f'<a href="{url}">View Tweet</a>'
                    f"</blockquote>"
                )

            # Plain text for embedding derived from the embed HTML
            embed_text = _strip_html(embed_html)

            preview_content = f"""# {preview_title}

<div class="twitter-embed-container">
{embed_html}
</div>

**Source:** [{url}]({url})"""

            logging.info(f"Created tweet preview for: {url}")
            return preview_title, preview_content, embed_text

        # Regular link preview for other URLs
        fetched = None
        try:
            downloaded = trafilatura.fetch_url(url)
            if downloaded:
                fetched = trafilatura.extract(downloaded, include_comments=False, include_tables=False)
        except Exception as fe:
            logging.info(f"Trafilatura fetch failed, using fallback: {fe}")

        preview_title = f"Link: {domain}"
        preview_content = f"# {preview_title}\n\n**URL:** {url}\n\n*Click to visit the original source*"
        logging.info(f"Created preview for: {url}")
        # For non-Twitter pages, prefer fetched article text for embeddings
        embed_source = fetched if fetched and len(fetched) > 40 else _strip_html(preview_content)
        return preview_title, preview_content, embed_source

    except Exception as e:
        logging.warning(f"Failed to create preview for {url}: {e}")
        return None, None, None

def extract_title(content, original_url=None):
    """Extract title from markdown content or use web title"""
    if original_url:
        return original_url
    
    lines = content.strip().split('\n')
    for line in lines:
        if line.startswith('# '):
            return line[2:].strip()
    # Fallback to first non-empty line or filename
    for line in lines:
        if line.strip():
            return line.strip()[:50]
    return "Untitled"

def parse_frontmatter_and_body(raw_text: str):
    """Parse optional YAML frontmatter. Returns (meta: dict, body: str)."""
    if raw_text.startswith('---'):
        parts = raw_text.split('\n', 1)[1]
        if '\n---' in parts:
            fm_text, body_rest = parts.split('\n---', 1)
            try:
                meta = yaml.safe_load(fm_text) or {}
                # Trim leading newline after end delimiter
                body = body_rest.lstrip('\n')
                return meta, body
            except Exception as e:
                logging.warning(f"Frontmatter parse error: {e}")
    return {}, raw_text


def chunk_text(text: str, max_chars: int = 1200, overlap: int = 150):
    """Simple chunking by paragraphs, merging until ~max_chars with overlap."""
    paragraphs = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]
    chunks = []
    current = []
    current_len = 0
    for p in paragraphs:
        if current_len + len(p) + 2 <= max_chars or not current:
            current.append(p)
            current_len += len(p) + 2
        else:
            chunks.append('\n\n'.join(current))
            # start next with overlap
            tail = ('\n\n'.join(current))[-overlap:]
            current = [tail, p]
            current_len = len(tail) + len(p) + 2
    if current:
        chunks.append('\n\n'.join(current))
    return chunks


def average_vectors(vectors):
    if not vectors:
        return None
    # simple element-wise mean
    n = len(vectors)
    m = len(vectors[0])
    summed = [0.0]*m
    for v in vectors:
        for i, val in enumerate(v):
            summed[i] += val
    return [x/n for x in summed]


def process_md_files():
    """Process all .md files in knowledge directory"""
    knowledge_dir = Path('knowledge')
    if not knowledge_dir.exists():
        knowledge_dir.mkdir()
        logging.info("Created knowledge directory")
    
    md_files = list(knowledge_dir.glob('*.md'))
    if not md_files:
        logging.warning("No .md files found in knowledge directory")
        return []
    
    knowledge_base = []

    # Load existing to support incremental with content hash
    prev_map = {}
    try:
        with open('embeddings.json', 'r', encoding='utf-8') as pf:
            prev_data = json.load(pf)
            for entry in prev_data:
                prev_map[entry.get('file')] = entry
    except Exception:
        prev_map = {}
    
    for md_file in md_files:
        logging.info(f"Processing {md_file.name}")
        
        with open(md_file, 'r', encoding='utf-8') as f:
            raw_text = f.read().strip()
        meta, content = parse_frontmatter_and_body(raw_text)
        
        if not content:
            logging.warning(f"Skipping empty file: {md_file.name}")
            continue
        
        original_content = content
        web_title = None
        is_url = False
        tags = meta.get('tags', []) if isinstance(meta, dict) else []
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(',') if t.strip()]
        
        # Check if content is just a URL
        if is_url_only(content):
            is_url = True
            url = content.strip()
            web_title, preview_content, preview_text = create_url_preview(url)
            if preview_content:
                # Use preview content for display, but embed text extracted from preview
                content = preview_content
                # Replace original_content with the URL only for clarity
                original_content = url
                logging.info(f"Created preview for {url}")
            else:
                logging.warning(f"Could not create preview for {url}, using URL as content")
        
        # Extract title (frontmatter title overrides)
        title = meta.get('title') or extract_title(content, web_title)
        
        # Generate embedding
        try:
            base_text_for_embedding = preview_text if is_url and 'preview_text' in locals() and preview_text else content
            content_hash = hashlib.sha256(base_text_for_embedding.encode('utf-8')).hexdigest()

            prev = prev_map.get(md_file.name)
            # File timestamps
            try:
                modified_ts = os.path.getmtime(md_file)
                created_ts = os.path.getctime(md_file)
            except Exception:
                modified_ts = 0
                created_ts = 0
            if prev and prev.get('content_hash') == content_hash:
                # Reuse previous entry as-is (fast path)
                prev['title'] = title
                prev['content'] = content
                prev['original_content'] = original_content
                prev['is_url'] = is_url
                prev['source_url'] = url if is_url else None
                prev['tags'] = tags
                # Preserve created_ts if present, otherwise set
                if 'created_ts' not in prev or not prev['created_ts']:
                    prev['created_ts'] = created_ts
                # Always update modified_ts from filesystem
                prev['modified_ts'] = modified_ts
                knowledge_base.append(prev)
                logging.info(f"✓ Unchanged {md_file.name}, reused embeddings")
                continue

            # Chunking
            text_chunks = chunk_text(base_text_for_embedding)
            chunk_embeddings = []
            chunk_objs = []
            for ch in text_chunks:
                emb = get_embedding(ch)
                chunk_embeddings.append(emb)
                chunk_objs.append({
                    'text': ch,
                    'embedding': emb
                })

            # Document-level embedding as average of chunks
            doc_embedding = average_vectors(chunk_embeddings) if chunk_embeddings else get_embedding(base_text_for_embedding)

            knowledge_base.append({
                'file': md_file.name,
                'title': title,
                'content': content,
                'original_content': original_content,
                'is_url': is_url,
                'source_url': url if is_url else None,
                'tags': tags,
                'chunks': chunk_objs,
                'embedding': doc_embedding,
                'content_hash': content_hash,
                'created_ts': created_ts,
                'modified_ts': modified_ts
            })
            
            logging.info(f"✓ Processed {md_file.name}: {title}")
            
        except Exception as e:
            logging.error(f"Failed to process {md_file.name}: {e}")
    
    return knowledge_base

def main():
    """Main build function"""
    logging.info("Starting knowledge base build...")
    
    # Process markdown files
    knowledge_base = process_md_files()
    
    if not knowledge_base:
        logging.error("No valid markdown files processed")
        return
    
    # Save embeddings
    with open('embeddings.json', 'w', encoding='utf-8') as f:
        json.dump(knowledge_base, f, ensure_ascii=False, separators=(',', ':'))
    
    # Calculate file sizes
    embeddings_size = os.path.getsize('embeddings.json')
    logging.info(f"Generated embeddings.json ({embeddings_size:,} bytes)")
    logging.info(f"Processed {len(knowledge_base)} documents")
    
    # Show size breakdown
    total_size = 0
    for file in ['app.py', 'templates/index.html', 'static/style.css', 'static/script.js']:
        if os.path.exists(file):
            size = os.path.getsize(file)
            total_size += size
            logging.info(f"{file}: {size:,} bytes")
    
    logging.info(f"Core application size: {total_size:,} bytes")
    logging.info("Build complete!")

if __name__ == '__main__':
    main()
