import { useState } from 'react'
import TagInput from './TagInput'
import RecipeCarousel from './RecipeCarousel'
import 'keen-slider/keen-slider.min.css'


function App() {
  const [ingredients, setIngredients] = useState<string[]>([])
  const [isLoading, setIsLoading] = useState(false)

  // TODO: Remove this once we have a real API call
  const dummyRecipes = [
    { title: 'Pancakes', ingredients: ['2 cups flour', '1 cup milk', '2 eggs', '1 cup sugar', '1 cup butter', '1 cup baking powder', '1 cup salt'] },
    { title: 'Omelette', ingredients: ['2 eggs', '1 cup cheese', '1 cup spinach', '1 cup onion', '1 cup tomato', '1 cup mushroom', '1 cup garlic'] },
    { title: 'Smoothie', ingredients: ['1 banana', '1 cup milk', '1 cup berries', '1 cup yogurt', '1 cup honey', '1 cup ice'] },
    { title: 'Pasta', ingredients: ['1 cup pasta', '1 cup sauce', '1 cup cheese', '1 cup onion', '1 cup garlic', '1 cup tomato'] },
    { title: 'Salad', ingredients: ['1 cup lettuce', '1 cup tomato', '1 cup cucumber'] }
  ]

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

          <RecipeCarousel recipes={dummyRecipes} />
        </div>
      </div>
    </div>
  )
}

export default App
