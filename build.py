#!/usr/bin/env python3
"""
Build script to process .md files and generate embeddings
Run this script to update the knowledge base when adding new .md files
"""
import os
import json
import logging
from pathlib import Path
from openai import OpenAI

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

def extract_title(content):
    """Extract title from markdown content"""
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
        
        # Extract title
        title = extract_title(content)
        
        # Generate embedding
        try:
            embedding = get_embedding(content)
            
            # Get file modification timestamp
            modified_time = int(md_file.stat().st_mtime)
            
            knowledge_base.append({
                'file': md_file.name,
                'title': title,
                'content': content,
                'embedding': embedding,
                'modified': modified_time
            })
            
            logging.info(f"✓ Processed {md_file.name}: {title}")
            
        except Exception as e:
            logging.error(f"Failed to process {md_file.name}: {e}")
    
    return knowledge_base

def should_rebuild():
    """Check if rebuild is needed based on file timestamps"""
    if not os.path.exists('embeddings.json'):
        return True
    
    try:
        with open('embeddings.json', 'r', encoding='utf-8') as f:
            existing = json.load(f)
            existing_files = {item['file']: item.get('modified', 0) for item in existing}
    except:
        return True
    
    knowledge_dir = Path('knowledge')
    for md_file in knowledge_dir.glob('*.md'):
        current_modified = int(md_file.stat().st_mtime)
        if md_file.name not in existing_files or current_modified > existing_files[md_file.name]:
            return True
    
    return False

def main():
    """Main build function with incremental updates"""
    if not should_rebuild():
        logging.info("No changes detected, embeddings up to date")
        return
        
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
