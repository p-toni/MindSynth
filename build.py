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

def create_url_preview(url):
    """Create URL preview with embed support for Twitter/X"""
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        domain = parsed.netloc.replace('www.', '')
        
        # Check if it's a Twitter/X URL
        if 'twitter.com' in domain or 'x.com' in domain:
            # Extract tweet ID for embed
            tweet_id = url.split('/')[-1].split('?')[0]
            preview_title = f"Tweet Preview"
            # Use data attribute to identify twitter embeds
            preview_content = f"""# {preview_title}

<div class="twitter-embed-container">
    <blockquote class="twitter-tweet" data-dnt="true" data-theme="light">
        <a href="{url}">View Tweet</a>
    </blockquote>
</div>

**Source:** [{url}]({url})"""
        else:
            # Regular link preview for other URLs
            preview_title = f"Link: {domain}"
            preview_content = f"# {preview_title}\n\n**URL:** {url}\n\n*Click to visit the original source*"
        
        logging.info(f"Created preview for: {url}")
        return preview_title, preview_content
    except Exception as e:
        logging.warning(f"Failed to create preview for {url}: {e}")
        return None, None

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
            web_title, preview_content = create_url_preview(url)
            if preview_content:
                # Use preview content for embedding
                content = preview_content
                logging.info(f"Created preview for {url}")
            else:
                logging.warning(f"Could not create preview for {url}, using URL as content")
        
        # Extract title
        title = extract_title(content, web_title)
        
        # Generate embedding
        try:
            embedding = get_embedding(content)
            
            knowledge_base.append({
                'file': md_file.name,
                'title': title,
                'content': content,
                'original_content': original_content,
                'is_url': is_url,
                'source_url': content.strip() if is_url else None,
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
