// TagInput.tsx
import { useState, useRef } from 'react'

interface TagInputProps {
  tags: string[]
  setTags: (tags: string[]) => void
}

const TagInput = ({ tags, setTags }: TagInputProps) => {
  const [input, setInput] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)

  const addTag = () => {
    const trimmed = input.trim()
    if (trimmed && !tags.includes(trimmed)) {
      setTags([...tags, trimmed])
    }
    setInput('')
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault()
      addTag()
    } else if (e.key === 'Backspace' && input === '' && tags.length > 0) {
      setTags(tags.slice(0, -1))
    }
  }

  const removeTag = (index: number) => {
    setTags(tags.filter((_, i) => i !== index))
  }

  return (
    <div className="border rounded-lg px-3 py-2 flex flex-wrap items-center gap-2 focus-within:ring-2 focus-within:ring-blue-500 cursor-text" onClick={() => inputRef.current?.focus()}>
      {tags.map((tag, i) => (
        <span key={i} className="bg-blue-100 text-blue-700 px-2 py-1 rounded-full text-sm flex items-center">
          {tag}
          <button
            type="button"
            onClick={() => removeTag(i)}
            className="ml-1 text-blue-500 hover:text-blue-700"
          >
            ×
          </button>
        </span>
      ))}
        <input
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            className="w-auto min-w-[50px] max-w-full flex-1 outline-none py-1"
            placeholder={tags.length === 0 ? 'Type and press Enter or comma' : ''}
        />
    </div>
  )
}

export default TagInput
