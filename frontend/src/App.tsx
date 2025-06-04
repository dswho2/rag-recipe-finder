import { useState } from 'react'

function App() {
  const [ingredients, setIngredients] = useState<string>('')
  const [isLoading, setIsLoading] = useState<boolean>(false)
  const [recipes, setRecipes] = useState<any[]>([])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    // TODO: Implement API call to backend
    setIsLoading(false)
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
              <label htmlFor="ingredients" className="block text-gray-700 text-sm font-bold mb-2">
                Enter your ingredients
              </label>
              <textarea
                id="ingredients"
                value={ingredients}
                onChange={(e) => setIngredients(e.target.value)}
                placeholder="Enter ingredients separated by commas (e.g., eggs, milk, flour)"
                className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                rows={4}
              />
            </div>
            <button
              type="submit"
              disabled={isLoading || !ingredients.trim()}
              className="w-full bg-blue-500 text-white font-bold py-2 px-4 rounded-lg hover:bg-blue-600 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
            >
              {isLoading ? 'Finding Recipes...' : 'Find Recipes'}
            </button>
          </form>

          {recipes.length > 0 && (
            <div className="space-y-4">
              <h2 className="text-2xl font-bold text-gray-900 mb-4">Found Recipes</h2>
              {recipes.map((recipe, index) => (
                <div key={index} className="bg-white shadow-md rounded-lg p-6">
                  <h3 className="text-xl font-bold text-gray-900 mb-2">{recipe.title}</h3>
                  <div className="text-gray-600">
                    <p className="font-semibold mb-1">Ingredients:</p>
                    <p>{recipe.ingredients.join(', ')}</p>
                  </div>
                  <button
                    className="mt-4 text-blue-500 hover:text-blue-600 font-medium"
                    onClick={() => {/* TODO: Implement recipe selection */}}
                  >
                    View Full Recipe
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default App
