// src/api/recipes.ts

export interface Recipe {
    title: string;
    description?: string;
    ingredients: string[];
    instructions?: string;
    missing?: string[];
  }

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
  
  export async function fetchRecipeSuggestions(
    ingredients: string[],
    count: number
  ): Promise<Recipe[]> {
    const response = await fetch(`${API_BASE}/api/recipes/suggest-multiple`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ingredients, count })
    })
  
    if (!response.ok) {
      throw new Error("Failed to fetch suggestions")
    }
  
    return await response.json()
  }
  