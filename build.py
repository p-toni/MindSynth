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

def fetch_web_content(url):
    """Fetch and extract content from a URL"""
    try:
        logging.info(f"Fetching content from: {url}")
        downloaded = trafilatura.fetch_url(url)
        if downloaded:
            content = trafilatura.extract(downloaded, include_comments=False, include_tables=False)
            title = trafilatura.extract(downloaded, include_comments=False, include_tables=False, output_format='xml')
            if title:
                # Extract title from XML metadata
                title_match = re.search(r'<title[^>]*>(.*?)</title>', title)
                if title_match:
                    title = title_match.group(1).strip()
                else:
                    title = content.split('\n')[0][:100] if content else url
            else:
                title = url
            return title, content
        return None, None
    except Exception as e:
        logging.warning(f"Failed to fetch content from {url}: {e}")
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
            web_title, web_content = fetch_web_content(url)
            if web_content:
                # Use web content for embedding but keep original URL
                content = f"# {web_title}\n\nSource: {url}\n\n{web_content}"
                logging.info(f"Fetched web content for {url}")
            else:
                logging.warning(f"Could not fetch content for {url}, using URL as content")
        
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
