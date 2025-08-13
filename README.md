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

### Vercel Deployment (Recommended)

1. **Fork this repository** to your GitHub account

2. **Connect to Vercel**:
   - Go to [vercel.com](https://vercel.com)
   - Import your GitHub repository
   - Vercel will auto-detect the Flask app

3. **Set Environment Variables** in Vercel dashboard:
   - `OPENAI_API_KEY`: Your OpenAI API key
   - `SESSION_SECRET`: Random secure string

4. **Deploy**: Vercel will automatically deploy on every push to main

### Environment Variables

- `OPENAI_API_KEY`: Required for generating embeddings
- `SESSION_SECRET`: For secure sessions (optional)
- `FLASK_ENV`: Set to "production" for production

### Building Knowledge Base

The embedding generation is **fully automated**:

1. **Add markdown files** to the `knowledge/` directory
2. **Create a Pull Request** with your new knowledge
3. **Merge the PR** - GitHub Actions automatically:
   - Generates embeddings using OpenAI API
   - Commits the updated `embeddings.json`
   - Triggers Vercel deployment
4. **Your knowledge is instantly searchable** at toni.ltd

#### Manual Build (Optional)
For local development, you can still build manually:
```bash
python build.py
```

### Custom Domain (toni.ltd)

To use your custom domain:
1. In Vercel dashboard, go to your project settings
2. Add `toni.ltd` as a custom domain
3. Configure DNS to point to Vercel

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
# Force deployment trigger
