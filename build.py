#!/usr/bin/env python3
"""
Build script to process .md files and generate embeddings
Run this script to update the knowledge base when adding new .md files
"""
import os
import json
import logging
import re
from pathlib import Path
from openai import OpenAI
import trafilatura
from urllib.parse import urlparse, quote
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
import html as html_lib

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
    """Create URL preview with embed support for Twitter/X, with text for embedding."""
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
        preview_title = f"Link: {domain}"
        preview_content = f"# {preview_title}\n\n**URL:** {url}\n\n*Click to visit the original source*"
        logging.info(f"Created preview for: {url}")
        # For non-Twitter pages, embed the preview text itself
        return preview_title, preview_content, _strip_html(preview_content)

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
    
    for md_file in md_files:
        logging.info(f"Processing {md_file.name}")
        
        with open(md_file, 'r', encoding='utf-8') as f:
            content = f.read().strip()
        
        if not content:
            logging.warning(f"Skipping empty file: {md_file.name}")
            continue
        
        original_content = content
        web_title = None
        is_url = False
        
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
        
        # Extract title
        title = extract_title(content, web_title)
        
        # Generate embedding
        try:
            # If URL-only and we built a preview, use extracted text for embeddings
            text_for_embedding = preview_text if is_url and 'preview_text' in locals() and preview_text else content
            embedding = get_embedding(text_for_embedding)
            
            knowledge_base.append({
                'file': md_file.name,
                'title': title,
                'content': content,
                'original_content': original_content,
                'is_url': is_url,
                'source_url': url if is_url else None,
                'embedding': embedding
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
