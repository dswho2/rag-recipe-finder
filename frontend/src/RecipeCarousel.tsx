// RecipeCarousel.tsx
import { useKeenSlider } from 'keen-slider/react'
import 'keen-slider/keen-slider.min.css'
import { useState } from 'react'
import { ChevronLeft, ChevronRight } from 'lucide-react'

interface Recipe {
  title: string
  ingredients: string[]
  description?: string
  instructions?: string
  missing?: string[]
}

interface RecipeCarouselProps {
  recipes: Recipe[]
  onView: (recipe: Recipe) => void
}

const RecipeCarousel = ({ recipes, onView }: RecipeCarouselProps) => {
  const [currentSlide, setCurrentSlide] = useState(0)
  const [loaded, setLoaded] = useState(false)

  const [sliderRef, instanceRef] = useKeenSlider<HTMLDivElement>({
    initial: 0,
    slides: {
      perView: 2.5,
      spacing: 16,
      origin: 'center',
    },
    breakpoints: {
      '(min-width: 640px)': {
        slides: { perView: 2.2, spacing: 20, origin: 'center' },
      },
      '(min-width: 768px)': {
        slides: { perView: 2.5, spacing: 24, origin: 'center' },
      },
      '(min-width: 1024px)': {
        slides: { perView: 3, spacing: 28, origin: 'center' },
      },
    },
    mode: 'snap',
    slideChanged(slider) {
      setCurrentSlide(slider.track.details.rel)
    },
    created() {
      setLoaded(true)
    },
  })

  return (
    <div className="mt-8 relative">
      <h2 className="text-2xl font-bold text-gray-900 mb-4">Recipe Suggestions</h2>

      <div ref={sliderRef} className="keen-slider mx-auto">
        {recipes.map((recipe, i) => (
          <div
            key={i}
            className="keen-slider__slide bg-white shadow-md rounded-lg p-4 max-w-sm h-[260px] flex flex-col"
          >
            <div className="flex-grow overflow-hidden">
              <h3 className="text-lg font-bold mb-2">{recipe.title}</h3>
              <div className="relative h-full overflow-hidden">
                <ul className="text-gray-700 text-sm space-y-1">
                  {recipe.missing?.map((item, idx) => (
                    <li key={`m-${idx}`} className="text-red-600">• {item} <span className="italic text-xs">(missing)</span></li>
                  ))}
                  {recipe.ingredients.slice(0, 6 - (recipe.missing?.length ?? 0)).map((ingredient, idx) => (
                    <li key={`i-${idx}`}>• {ingredient}</li>
                  ))}
                </ul>

                {recipe.ingredients.length + (recipe.missing?.length ?? 0) > 6 && (
                  <div className="relative">
                    <div className="absolute -top-3 left-0 right-0 h-6 bg-gradient-to-t from-white to-transparent pointer-events-none z-0" />
                    <div className="relative -mt-2 text-center text-xl text-gray-400 z-10 pointer-events-none">
                      …
                    </div>
                  </div>
                )}
              </div>
            </div>

            <button
              className="mt-auto pt-2 text-blue-500 hover:underline font-medium"
              onClick={() => onView(recipe)}
            >
              View Recipe
            </button>
          </div>
        ))}
      </div>

      {loaded && instanceRef.current && (
        <>
          <button
            onClick={() => instanceRef.current?.prev()}
            className="absolute left-0 top-1/2 -translate-y-1/2 bg-white shadow-md rounded-full p-2 hover:bg-gray-100 z-10 transition hover:scale-105"
            aria-label="Previous"
          >
            <ChevronLeft className="w-5 h-5 text-gray-700" />
          </button>
          <button
            onClick={() => instanceRef.current?.next()}
            className="absolute right-0 top-1/2 -translate-y-1/2 bg-white shadow-md rounded-full p-2 hover:bg-gray-100 z-10 transition hover:scale-105"
            aria-label="Next"
          >
            <ChevronRight className="w-5 h-5 text-gray-700" />
          </button>
        </>
      )}

      {loaded && instanceRef.current && (
        <div className="flex justify-center mt-4 gap-2">
          {recipes.map((_, idx) => (
            <button
              key={idx}
              onClick={() => instanceRef.current?.moveToIdx(idx)}
              className={`w-3 h-3 rounded-full transition-colors ${
                currentSlide === idx ? 'bg-blue-500' : 'bg-gray-300'
              }`}
            />
          ))}
        </div>
      )}
    </div>
  )
}

export default RecipeCarousel
