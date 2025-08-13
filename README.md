# MindSynth

A personal knowledge base application that provides semantic search functionality over markdown documents with an innovative dot-based visualization system. Search through your thoughts using AI-powered semantic search with rich hover previews.

## Features

- **Semantic Search**: Understands meaning, not just keywords, using OpenAI embeddings
- **Dot Visualization**: Documents represented as variable-sized dots based on semantic relevance  
- **Rich Hover Tooltips**: Dynamic preview cards with title, summary, match percentage, and tags
- **Literary Design**: Contemplative, scholarly aesthetic with serif typography
- **Lightweight**: Ultra-minimal footprint while delivering powerful search capabilities
- **Private**: Your knowledge stays on your server

## Quick Start

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd MindSynth
   ```

2. **Install dependencies**
   ```bash
   python -m pip install -e .
   ```

3. **Set up environment**
   ```bash
   cp .env.example .env
   # Edit .env with your OpenAI API key
   ```

4. **Add knowledge**
   ```bash
   # Add .md files to the knowledge/ directory
   # Then build embeddings:
   python build.py
   ```

5. **Run the application**
   ```bash
   python app.py
   ```

## Deployment

### Environment Variables

- `OPENAI_API_KEY`: Required for generating embeddings
- `SESSION_SECRET`: For secure sessions (optional)

### Building Knowledge Base

After adding markdown files to `knowledge/`, run:

```bash
python build.py
```

This will generate `embeddings.json` with semantic vectors for search.

## Architecture

- **Frontend**: Vanilla JavaScript with dot-based visualization
- **Backend**: Flask with OpenAI integration
- **Search**: Cosine similarity over text embeddings
- **Storage**: File-based markdown with JSON embeddings cache

## Knowledge Format

Add `.md` files to the `knowledge/` directory. Supports:

- Standard markdown formatting
- Optional YAML frontmatter for metadata
- URL-only files (creates automatic previews)
- Twitter/X embed support

Example:
```markdown
---
title: "My Thoughts on AI"
tags: ["ai", "technology", "future"]
---

# My Thoughts on AI

Content goes here...
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

MIT License - see LICENSE file for details.

---

*A place for ideas to find each other*
