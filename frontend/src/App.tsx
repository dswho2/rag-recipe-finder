// App.tsx
import { useState } from 'react'
import TagInput from './TagInput'
import RecipeCarousel from './RecipeCarousel'
import 'keen-slider/keen-slider.min.css'
import { fetchRecipeSuggestions } from './api/recipes'

interface Recipe {
  title: string;
  description?: string;
  ingredients: string[];
  instructions?: string;
  missing?: string[];
}

const SUGGESTION_COUNT = 5

function App() {
  const [ingredients, setIngredients] = useState<string[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [recipes, setRecipes] = useState<Recipe[]>([])
  const [error, setError] = useState<string | null>(null)
  const [selectedRecipe, setSelectedRecipe] = useState<Recipe | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    setError(null)
    try {
      const data = await fetchRecipeSuggestions(ingredients, SUGGESTION_COUNT)
      setRecipes(data)
    } catch (err) {
      console.error(err)
      setError("Something went wrong while fetching recipes. Please try again.")
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-100">
      <div className="container mx-auto px-4 py-8">
        <header className="text-center mb-12">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">RAG Recipe Finder</h1>
          <p className="text-lg text-gray-600">Find recipes based on your ingredients</p>
        </header>

        <div className="max-w-2xl mx-auto">
          <form onSubmit={handleSubmit} className="bg-white shadow-md rounded-lg p-6 mb-8">
            <div className="mb-4">
              <label className="block text-gray-700 text-sm font-bold mb-2">
                Enter your ingredients
              </label>
              <TagInput tags={ingredients} setTags={setIngredients} />
            </div>
            <button
              type="submit"
              disabled={isLoading || ingredients.length === 0}
              className="w-full bg-blue-500 text-white font-bold py-2 px-4 rounded-lg hover:bg-blue-600 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
            >
              {isLoading ? 'Finding Recipes...' : 'Find Recipes'}
            </button>
          </form>

          {error && (
            <div className="mb-4 px-4 py-2 bg-red-100 text-red-700 border border-red-400 rounded">
              {error}
            </div>
          )}

          {recipes.length > 0 && (
            <RecipeCarousel
              recipes={recipes}
              onView={(recipe) => setSelectedRecipe(recipe)}
            />
          )}
        </div>

        {selectedRecipe && (
          <div className="fixed inset-0 z-50 bg-black bg-opacity-50 flex items-center justify-center">
            <div className="bg-white rounded-lg p-6 max-w-lg w-full relative">
              <button
                onClick={() => setSelectedRecipe(null)}
                className="absolute top-2 right-2 text-gray-500 hover:text-gray-700"
              >
                ✕
              </button>
              <h2 className="text-2xl font-bold mb-2">{selectedRecipe.title}</h2>
              <p className="mb-4 text-sm text-gray-500 italic">{selectedRecipe.description}</p>

              {selectedRecipe.missing && selectedRecipe.missing.length > 0 && (
                <>
                  <h3 className="font-semibold mb-1 text-red-600">Missing Ingredients:</h3>
                  <ul className="list-disc list-inside text-sm mb-4 text-red-600">
                    {selectedRecipe.missing.map((item: string, i: number) => (
                      <li key={i}>{item}</li>
                    ))}
                  </ul>
                </>
              )}

              <h3 className="font-semibold mb-1">Ingredients:</h3>
              <ul className="list-disc list-inside text-sm mb-4">
                {selectedRecipe.ingredients.map((item: string, i: number) => (
                  <li key={i}>{item}</li>
                ))}
              </ul>
              {selectedRecipe.instructions && (
                <>
                  <h3 className="font-semibold mb-1">Instructions:</h3>
                  <p className="text-sm whitespace-pre-line">{selectedRecipe.instructions}</p>
                </>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default App
