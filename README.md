# RAG Recipe Finder

A web app to find recipes based on ingredients user inputs, utilizing Retrieval-Augmented Generation (RAG).

## Features

- **Ingredient-Based Recipe Search**: Enter the ingredients you have, get personalized recipe suggestions
- **Smart Recipe Generation**: AI-powered recipe creation using your available ingredients
- **Recipe Database**: Access to a vast collection of recipes from multiple sources
- **Intelligent Matching**: Advanced algorithm to find the best recipe matches
- **User-Friendly Interface**: Clean, modern UI for seamless recipe discovery

## Technology Stack

- **Frontend**: React with Tailwind CSS
- **Backend**: FastAPI
- **Vector Database**: FAISS for efficient similarity search
- **Embeddings**: OpenAI's text-embedding-3-small
- **LLM**: OpenAI GPT API for recipe generation
- **Data Processing**: Python with pandas for recipe data handling
- **Web Scraping**: Playwright for recipe collection

## Project Structure

```
rag-recipe-finder/
├── backend/
│   ├── app/
│   │   ├── core/           # Core functionality
│   │   ├── models/         # Data models
│   │   ├── services/       # Business logic
│   │   └── api/           # API endpoints
│   ├── data/              # Recipe datasets
│   └── tests/             # Backend tests
├── frontend/
│   ├── src/
│   │   ├── components/    # React components
│   │   ├── pages/        # Page components
│   │   ├── services/     # API services
│   │   └── utils/        # Utility functions
│   └── public/           # Static assets
└── scripts/              # Utility scripts
```

## Pipeline Overview

1. **Recipe Data Ingestion**
   - Collection from multiple sources
   - Data cleaning and normalization
   - Embedding generation
   - Vector database storage

2. **User Query Processing**
   - Ingredient input normalization
   - Query embedding generation
   - Similarity search
   - Recipe retrieval and ranking

3. **Recipe Generation**
   - Context preparation
   - LLM-based recipe generation
   - Result formatting and presentation

