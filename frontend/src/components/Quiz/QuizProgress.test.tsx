import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import QuizProgress from './QuizProgress'
import { QuizProgress as QuizProgressType } from '../../services/api'

describe('QuizProgress', () => {
  it('renders progress correctly', () => {
    const progress: QuizProgressType = {
      current_index: 3,
      total_questions: 10,
      correct_answers: 2,
      completed: false
    }

    render(<QuizProgress progress={progress} />)

    expect(screen.getByText('3 of 10 questions')).toBeInTheDocument()
    expect(screen.getByText('3')).toBeInTheDocument() // Answered
    expect(screen.getByText('7')).toBeInTheDocument() // Remaining
    expect(screen.getByText('2')).toBeInTheDocument() // Correct
    expect(screen.getByText('67%')).toBeInTheDocument() // Accuracy
  })

  it('renders progress without correct answers', () => {
    const progress: QuizProgressType = {
      current_index: 0,
      total_questions: 5,
      completed: false
    }

    render(<QuizProgress progress={progress} />)

    expect(screen.getByText('0 of 5 questions')).toBeInTheDocument()
    expect(screen.getByText('0')).toBeInTheDocument() // Answered
    expect(screen.getByText('5')).toBeInTheDocument() // Remaining
    // Should not show correct answers and accuracy when no answers yet
    expect(screen.queryByText('Correct')).not.toBeInTheDocument()
    expect(screen.queryByText('Accuracy')).not.toBeInTheDocument()
  })

  it('calculates progress percentage correctly', () => {
    const progress: QuizProgressType = {
      current_index: 5,
      total_questions: 10,
      completed: false
    }

    render(<QuizProgress progress={progress} />)

    // Check that progress bar is 50% (5/10)
    const progressBar = document.querySelector('.bg-blue-600')
    expect(progressBar).toHaveStyle('width: 50%')
  })
})