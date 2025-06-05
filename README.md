# RAG Recipe Finder

A web app to find recipes based on ingredients user inputs, utilizing a Retrieval-Augmented Generation (RAG) pipeline.

## Features

- **Ingredient-Based Recipe Search**: Enter the ingredients you have, get personalized recipe suggestions
- **Smart Recipe Generation**: AI-powered recipe creation using your available ingredients
- **Recipe Database**: Access to a vast collection of recipes from multiple sources
- **Intelligent Matching**: Advanced algorithm to find the best recipe matches
- **User-Friendly Interface**: Clean, modern UI for seamless recipe discovery

MVP Feature List:

- User inputs a list of ingredients
- App finds similar recipes using semantic search
- A language model adapts or generates a new recipe using retrieved data
- Display full recipe to user (display multiple for user to choose)

## Architecture Overview

### Technology Stack

#### Frontend Layer
- React + TypeScript
- Tailwind CSS for styling
- AWS S3 + CloudFront for hosting

#### Backend Layer
- AWS Lambda + API Gateway
- Python virtual environment (venv) for dependency management
- LangChain for RAG pipeline
- OpenAI API for embeddings and generation
- AWS DynamoDB for structured data
- Pinecone for vector storage

#### Authentication (if added)
- Amazon Cognito or Clerk

### Database Design

#### DynamoDB Schema (Recipes Table)
```
{
    recipe_id: string (partition key),
    title: string,
    ingredients: string[],
    steps: string[] | string,
    tags: string[],
    source: string,
    embedding_id: string
}
```

#### Pinecone Vector Store
- Vectors indexed by recipe_id
- 1536-dimensional embeddings (OpenAI text-embedding-3-small)
- Stores recipe text embeddings (title + ingredients)


## RAG Pipeline Flow

### 1. User Input Processing
- The user submits a list of ingredients via the frontend interface.
- The input text is embedded using OpenAI's embedding model (`text-embedding-3-small`).

### 2. Recipe Retrieval
- A Lambda function queries Pinecone for the top K most semantically similar recipes.
- For each retrieved vector ID, the corresponding full recipe data is fetched from DynamoDB.
- The backend returns a list of recipe previews (title, ingredients, tags) to the frontend.

> At this point, the user sees a selection of relevant recipes to choose from.

### 3. User Selection and Optional Recipe Generation
- The user can select a specific recipe to:
  - View the full recipe details, or
  - Generate a new recipe variation using GPT.
- If the user chooses to generate:
  - The selected recipe(s) are included in a prompt.
  - OpenAI's language model generates a tailored recipe.
  - The response is formatted and returned to the frontend.

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

## Setup

### Frontend Setup
1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Start the development server:
```bash
npm run dev
```

### Backend Setup

1. Navigate to the backend directory:
```bash
cd backend
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
# On Windows:
.\venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
Create a `.env` file in the backend directory with:
```
OPENAI_API_KEY=your_openai_key
PINECONE_API_KEY=your_pinecone_key
PINECONE_INDEX_NAME=your_index_name
```

5. Start the development server:
```bash
uvicorn app.main:app --reload
```

## Development Roadmap

### Phase 1: Infrastructure Setup
- [ ] AWS account configuration
- [ ] Pinecone setup
- [ ] S3 bucket and CloudFront distribution
- [ ] React + TypeScript frontend scaffold
- [ ] Poetry initialization and dependency setup

### Phase 2: Backend Development
- [ ] Lambda function implementation
- [ ] LangChain + Pinecone + DynamoDB integration
- [ ] Query embedding and retrieval logic

### Phase 3: Data Pipeline
- [ ] Recipe dataset processing
- [ ] Data normalization (units, ingredients)
- [ ] Embedding generation
- [ ] Database population

### Phase 4: MVP Integration
- [ ] Frontend-backend integration
- [ ] RAG pipeline testing
- [ ] Recipe display implementation

### Phase 5: Optional Features
- [ ] User authentication
- [ ] Recipe saving functionality
- [ ] Custom recipe submission

## Development Tools

| Category | Tools |
|----------|--------|
| Lambda Deployment | AWS SAM / Serverless Framework |
| API Testing | Postman / curl |
| Secrets | Lambda env vars / AWS Secrets Manager |
| Monitoring | AWS CloudWatch |
| CI/CD | GitHub Actions |
| Data Processing | LangChain + Pinecone Client |
| Backend Dependencies | Python venv + pip |

## Data Ingestion

### Data Sources
- Recipe1M dataset
- Scraped recipe websites
- User submissions (future)

### Processing Pipeline
1. Data collection and cleaning
2. Ingredient and unit normalization
3. Embedding generation
4. Database insertion
   - Recipe data → DynamoDB
   - Embeddings → Pinecone

## Testing

### DynamoDB Integration Tests
The following commands can be run from the `backend` directory to test DynamoDB integration:

```bash
# Run all DynamoDB tests in sequence
python -m pytest tests/test_dynamodb_connection.py -v

# Run individual operations:

# 1. Store a test recipe
python -m pytest tests/test_dynamodb_connection.py::test_store_recipe -v

# 2. Verify the stored recipe
python -m pytest tests/test_dynamodb_connection.py::test_get_recipe -v

# 3. Delete the test recipe
python -m pytest tests/test_dynamodb_connection.py::test_delete_recipe -v
```

These tests use a fixed test recipe ID (`test-recipe-001`) for consistency and easy verification in the AWS Console.
