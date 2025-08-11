# Overview

This is a personal knowledge base application that provides semantic search functionality over markdown documents with an innovative dot-based visualization system. Users store knowledge in markdown files and search through them using AI-powered semantic search with rich hover previews. The application maintains an ultra-lightweight footprint (14.1kB) while delivering powerful search capabilities through OpenAI's embedding models and an elegant "wall of dots" interface where dot size represents semantic relevance.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Frontend Architecture
- **Single Page Application**: Uses vanilla JavaScript with a minimal, responsive design
- **Dot Visualization System**: Documents represented as variable-sized dots (8px-24px) based on semantic relevance
- **Rich Hover Tooltips**: Dynamic JavaScript-generated preview cards with title, summary, match percentage, and tags
- **Modal System**: Full content displayed in overlays for detailed reading
- **Real-time Search**: Implements debounced search with instant visual feedback
- **Responsive Design**: Mobile-first approach with CSS Grid/Flexbox layout and adaptive tooltip sizing

## Backend Architecture
- **Flask Web Framework**: Lightweight Python web server for handling HTTP requests
- **RESTful API Design**: Clean separation between frontend and backend with JSON API endpoints
- **Modular Structure**: Separate modules for embedding generation (`build.py`) and web serving (`app.py`)
- **Environment-based Configuration**: Uses environment variables for sensitive data like API keys

## Data Processing Pipeline
- **Two-stage Architecture**: Build-time processing (embedding generation) and runtime serving
- **Embedding Generation**: Uses OpenAI's text-embedding-3-small model for vector representations
- **Similarity Search**: Implements cosine similarity for finding relevant documents
- **Content Preprocessing**: Automatic title extraction and metadata generation from markdown files

## Search Engine
- **Vector-based Search**: Converts user queries to embeddings and finds similar document embeddings
- **Semantic Understanding**: Goes beyond keyword matching to understand meaning and context
- **Real-time Query Processing**: Generates embeddings on-demand for user queries
- **Visual Relevance Indicators**: Dot size and color intensity represent cosine similarity scores
- **Rich Preview System**: Hover tooltips show detailed information without requiring clicks

## Content Management
- **File-based Storage**: Markdown files stored in a dedicated `knowledge/` directory
- **Static Embedding Cache**: Pre-computed embeddings stored in JSON format for fast retrieval
- **Build System**: Separate build process to regenerate embeddings when content changes
- **Automatic Content Discovery**: Scans directory for markdown files during build process
- **URL Preview System**: Automatically detects when .md files contain only URLs and creates lightweight previews without full content fetching
- **Smart URL Processing**: URLs are converted to searchable preview entries showing domain and source link

# External Dependencies

## OpenAI Integration
- **API Service**: OpenAI API for generating text embeddings
- **Model**: text-embedding-3-small for efficient and accurate semantic representations
- **Authentication**: API key-based authentication via environment variables

## Core Libraries
- **Flask**: Web framework for HTTP server and routing
- **NumPy**: Mathematical operations for vector similarity calculations
- **Python Markdown**: Rendering markdown content to HTML in modals
- **Pathlib**: Modern file system operations for content discovery
- **Trafilatura**: Web content extraction for fetching and processing articles from URLs
- **Regular Expressions**: URL pattern detection and content parsing

## Development Dependencies
- **Logging**: Built-in Python logging for debugging and monitoring
- **JSON**: Standard library for data serialization and storage
- **Environment Variables**: Configuration management for sensitive data

## Browser Dependencies
- **Modern JavaScript**: ES6+ features for frontend functionality
- **CSS3**: Advanced styling with gradients, transitions, and responsive design
- **HTML5**: Semantic markup with proper accessibility considerations