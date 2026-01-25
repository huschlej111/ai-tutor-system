import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import QuizQuestionCard from './QuizQuestionCard'
import { QuizQuestion, AnswerResult } from '../../services/api'

const mockQuestion: QuizQuestion = {
  term_id: '1',
  term: 'API Gateway',
  question_number: 1,
  total_questions: 5
}

const mockAnswerResult: AnswerResult = {
  session_id: 'session-1',
  evaluation: {
    is_correct: true,
    similarity_score: 0.85,
    feedback: 'Correct! Well done.',
    correct_answer: 'A service that acts as a front door for applications'
  },
  progress: {
    current_index: 1,
    total_questions: 5,
    correct_answers: 1,
    completed: false
  },
  next_question: {
    term_id: '2',
    term: 'Lambda',
    question_number: 2,
    total_questions: 5
  },
  quiz_completed: false
}

describe('QuizQuestionCard', () => {
  it('renders question correctly', () => {
    const mockOnSubmit = vi.fn()
    const mockOnNext = vi.fn()

    render(
      <QuizQuestionCard
        question={mockQuestion}
        onSubmitAnswer={mockOnSubmit}
        isSubmitting={false}
        lastResult={null}
        onNextQuestion={mockOnNext}
      />
    )

    expect(screen.getByText('API Gateway')).toBeInTheDocument()
    expect(screen.getByText('Question 1 of 5')).toBeInTheDocument()
    expect(screen.getByText('What is the definition of this term?')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('Enter your definition here...')).toBeInTheDocument()
  })

  it('submits answer when form is submitted', async () => {
    const mockOnSubmit = vi.fn()
    const mockOnNext = vi.fn()

    render(
      <QuizQuestionCard
        question={mockQuestion}
        onSubmitAnswer={mockOnSubmit}
        isSubmitting={false}
        lastResult={null}
        onNextQuestion={mockOnNext}
      />
    )

    const textarea = screen.getByPlaceholderText('Enter your definition here...')
    const submitButton = screen.getByText('Submit Answer')

    fireEvent.change(textarea, { target: { value: 'A service for APIs' } })
    fireEvent.click(submitButton)

    await waitFor(() => {
      expect(mockOnSubmit).toHaveBeenCalledWith('A service for APIs')
    })
  })

  it('shows result when lastResult is provided', async () => {
    const mockOnSubmit = vi.fn()
    const mockOnNext = vi.fn()

    const { rerender } = render(
      <QuizQuestionCard
        question={mockQuestion}
        onSubmitAnswer={mockOnSubmit}
        isSubmitting={false}
        lastResult={null}
        onNextQuestion={mockOnNext}
      />
    )

    // Initially should show the form
    expect(screen.getByPlaceholderText('Enter your definition here...')).toBeInTheDocument()

    // Rerender with result
    rerender(
      <QuizQuestionCard
        question={mockQuestion}
        onSubmitAnswer={mockOnSubmit}
        isSubmitting={false}
        lastResult={mockAnswerResult}
        onNextQuestion={mockOnNext}
      />
    )

    await waitFor(() => {
      expect(screen.getByText('Correct!')).toBeInTheDocument()
    })
    
    expect(screen.getByText('Correct! Well done.')).toBeInTheDocument()
    expect(screen.getByText('Similarity Score: 85%')).toBeInTheDocument()
    expect(screen.getByText('Next Question')).toBeInTheDocument()
  })

  it('disables submit button when submitting', () => {
    const mockOnSubmit = vi.fn()
    const mockOnNext = vi.fn()

    render(
      <QuizQuestionCard
        question={mockQuestion}
        onSubmitAnswer={mockOnSubmit}
        isSubmitting={true}
        lastResult={null}
        onNextQuestion={mockOnNext}
      />
    )

    const submitButton = screen.getByRole('button', { name: /evaluating/i })
    expect(submitButton).toBeDisabled()
  })

  it('calls onNextQuestion when next button is clicked', async () => {
    const mockOnSubmit = vi.fn()
    const mockOnNext = vi.fn()

    const { rerender } = render(
      <QuizQuestionCard
        question={mockQuestion}
        onSubmitAnswer={mockOnSubmit}
        isSubmitting={false}
        lastResult={null}
        onNextQuestion={mockOnNext}
      />
    )

    // Rerender with result to show next button
    rerender(
      <QuizQuestionCard
        question={mockQuestion}
        onSubmitAnswer={mockOnSubmit}
        isSubmitting={false}
        lastResult={mockAnswerResult}
        onNextQuestion={mockOnNext}
      />
    )

    await waitFor(() => {
      const nextButton = screen.getByText('Next Question')
      fireEvent.click(nextButton)
    })

    expect(mockOnNext).toHaveBeenCalled()
  })
})