# backend/app/services/langchain_service.py

from typing import List, Dict, Any, Optional
import json
from pydantic import BaseModel
from pydantic import RootModel
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain.output_parsers import PydanticOutputParser
from langchain.prompts import ChatPromptTemplate
from langchain_pinecone import PineconeVectorStore
from app.core.config import settings
from pinecone import Pinecone, ServerlessSpec

# Pydantic model for structured recipe output
class RecipeSchema(BaseModel):
    title: str
    description: Optional[str]
    ingredients: List[str]
    instructions: Optional[str]
    missing: Optional[List[str]] = []

class RecipeListModel(RootModel[List[RecipeSchema]]):
    pass

class LangChainService:
    def __init__(self):
        """Initialize LangChain components."""
        # Initialize embeddings with latest configuration
        self.embeddings = OpenAIEmbeddings(
            model=settings.EMBEDDING_MODEL,
            dimensions=settings.EMBEDDING_DIMENSIONS,
            openai_api_key=settings.OPENAI_API_KEY,
            tiktoken_model_name=settings.EMBEDDING_MODEL,  # Explicitly set tiktoken model
            show_progress_bar=True,  # Show progress when embedding multiple texts
            retry_min_seconds=1,  # Minimum seconds to wait between retries
            retry_max_seconds=10,  # Maximum seconds to wait between retries
            chunk_size=1000  # Process embeddings in chunks of 1000
        )
        
        # Initialize Pinecone
        self.pc = Pinecone(api_key=settings.PINECONE_API_KEY)
        
        # Get or create index
        if settings.PINECONE_INDEX_NAME not in [idx.name for idx in self.pc.list_indexes()]:
            self.pc.create_index(
                name=settings.PINECONE_INDEX_NAME,
                dimension=settings.EMBEDDING_DIMENSIONS,
                metric="cosine",
                spec=ServerlessSpec(
                    cloud="aws",
                    region=settings.AWS_REGION
                )
            )
        
        # Initialize vector store
        index = self.pc.Index(settings.PINECONE_INDEX_NAME)
        self.vector_store = PineconeVectorStore(
            index=index,
            embedding=self.embeddings,
            text_key="text"  # The metadata field that contains the text content
        )
        
        # Initialize chat model
        self.chat = ChatOpenAI(
            model=settings.CHAT_MODEL,
            temperature=settings.CHAT_MODEL_TEMPERATURE,
            openai_api_key=settings.OPENAI_API_KEY
        )
    
    async def generate_recipe_embedding(self, text: str) -> List[float]:
        """Generate embedding for recipe text."""
        return await self.embeddings.aembed_query(text)
    
    async def similar_recipes_query(self, query: str, k: int = 3) -> List[Dict[str, Any]]:
        """Find similar recipes using vector similarity."""
        # Use the latest async similarity search pattern
        docs_and_scores = await self.vector_store.asimilarity_search_with_relevance_scores(
            query,
            k=k
        )
        
        # Process results with additional metadata
        return [
            {
                "content": doc.page_content,
                "metadata": doc.metadata,
                "score": score,
                "distance": 1 - score  # Add cosine distance for reference
            }
            for doc, score in docs_and_scores
        ]

    # Generate multiple structured recipes in a single GPT call
    async def generate_multiple_recipes(
        self, ingredients: List[str], context: List[Dict[str, Any]], count: int = 5
    ) -> List[Dict[str, Any]]:
        context_text = "\n\n".join(
            f"""{item.get('metadata', {}).get('title', '')}:
    Ingredients: {', '.join(item.get('metadata', {}).get('ingredients', []))}
    {item.get('metadata', {}).get('instructions', '')}"""
            for item in context
        )

        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a helpful AI chef. You generate creative, realistic recipes based on the user's ingredients."),
            ("user", (
                "Here are example recipes:\n\n{context}\n\n"
                "Now based only on the ingredients below:\n{ingredients}\n\n"
                f"Generate {count} diverse recipes. Each recipe must include:\n"
                "- title\n- description\n- ingredients (used + common pantry items)\n"
                "- instructions\n- a field called `missing` listing ingredients not provided by the user (max 3 per recipe)\n\n"
                "Respond only with a JSON array like this:\n"
                "[{{\"title\": \"...\", \"description\": \"...\", \"ingredients\": [\"...\"], \"instructions\": \"...\", \"missing\": [\"...\"]}}]"
            )),
        ])

        parser = PydanticOutputParser(pydantic_object=RecipeListModel)
        chain = prompt | self.chat | parser

        result = await chain.ainvoke({
            "context": context_text,
            "ingredients": ", ".join(ingredients),
            "count": count
        })

        return [r.dict() for r in result.root]
    
    # Generate a single recipe suggestion (legacy version)
    async def generate_recipe_suggestion(self, ingredients: List[str], context: List[Dict[str, Any]]) -> str:
        """Generate recipe suggestions based on ingredients and similar recipes."""
        # Create prompt template
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a helpful cooking assistant. Given a list of ingredients and some similar recipes, 
            suggest a recipe that could be made. Focus on practical, achievable recipes."""),
            ("user", """Ingredients: {ingredients}
            
            Similar recipes for reference:
            {context}
            
            Please suggest a recipe that could be made with these ingredients, taking inspiration from the similar recipes.
            Include title, brief description, ingredients needed (marking which ones are missing from the provided list),
            and step-by-step instructions.""")
        ])
        
        # Format context
        context_str = "\n".join([
            f"Recipe: {item['metadata']['title']}\n"
            f"Ingredients: {', '.join(item['metadata']['ingredients'])}\n"
            for item in context
        ])
        
        # Create chain
        chain = prompt | self.chat | StrOutputParser()
        
        # Run chain
        response = await chain.ainvoke({
            "ingredients": ", ".join(ingredients),
            "context": context_str
        })
        
        return response
    
    # Store vector embedding of recipe text with metadata
    async def store_recipe_embedding(self, recipe_id: str, text: str, metadata: Dict[str, Any]):
        """Store recipe embedding in vector store."""
        # Use latest async add_texts pattern with namespace support
        await self.vector_store.aadd_texts(
            texts=[text],
            metadatas=[metadata],
            ids=[recipe_id],
            batch_size=100,  # Process in batches for better performance
            show_progress=True,  # Show progress bar for large operations
            namespace="recipes"  # Optional namespace for organization
        ) 