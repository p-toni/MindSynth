# Overview

This is a personal knowledge base application that provides semantic search functionality over markdown documents. The system allows users to store their knowledge in markdown files and search through them using AI-powered semantic search rather than simple keyword matching. The application is designed to be ultra-lightweight (under 14kB) while providing powerful search capabilities through OpenAI's embedding models.

# User Preferences

Preferred communication style: Simple, everyday language.
Design philosophy: "things should be subtle, aesthetic comes from taste" - values restraint over obvious effects.
Visual preferences: Clean minimalism with purposeful design choices, avoid excessive patterns or grids.
Circuit board aesthetics: Prefers authentic PCB patterns over simple grids - referenced CodePen examples for realistic trace routing and component placement.
Color scheme: Evolved from monochrome to dark neon theme - black background with blue (#3498db) glitch accents.
Glitch effects: Implemented pulsing grid background and subtle neon border effects as requested.

# System Architecture

## Frontend Architecture
- **Card-Based Layout**: Modern portfolio-inspired grid design with distinct functional areas
- **Modal System**: Content is displayed in overlays for better user experience
- **Real-time Search**: Implements debounced search with instant results as users type
- **Keyboard Navigation**: Full arrow key navigation with Enter to select, Escape to close
- **Search State Persistence**: Maintains query state in URL without complex routing
- **Responsive Design**: CSS Grid layout that adapts from 3-column to single-column on mobile

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
- **Enhanced Ranking**: Composite scoring with similarity * (1 + length_bonus + recency_bonus)
- **Semantic Understanding**: Goes beyond keyword matching to understand meaning and context
- **Real-time Query Processing**: Generates embeddings on-demand for user queries
- **Relevance Scoring**: Uses enhanced cosine similarity with document metadata weighting

## Content Management
- **File-based Storage**: Markdown files stored in a dedicated `knowledge/` directory
- **Smart Embedding Cache**: Pre-computed embeddings with file modification timestamps
- **Incremental Updates**: Build system only regenerates embeddings for changed files
- **Build System**: Separate build process with intelligent cache invalidation
- **Automatic Content Discovery**: Scans directory for markdown files during build process

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

## Development Dependencies
- **Logging**: Built-in Python logging for debugging and monitoring
- **JSON**: Standard library for data serialization and storage
- **Environment Variables**: Configuration management for sensitive data

## Browser Dependencies
- **Modern JavaScript**: ES6+ features for frontend functionality
- **CSS3**: Advanced styling with gradients, transitions, and responsive design
- **HTML5**: Semantic markup with proper accessibility considerations