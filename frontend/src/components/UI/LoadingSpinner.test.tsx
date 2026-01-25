import { describe, it, expect } from 'vitest'
import { render } from '@testing-library/react'
import LoadingSpinner from './LoadingSpinner'

describe('LoadingSpinner', () => {
  it('renders with default props', () => {
    const { container } = render(<LoadingSpinner />)
    
    const spinnerContainer = container.firstChild as HTMLElement
    expect(spinnerContainer).toHaveClass('flex', 'items-center', 'justify-center')
    
    const spinner = spinnerContainer.querySelector('.animate-spin')
    expect(spinner).toBeInTheDocument()
    expect(spinner).toHaveClass('animate-spin', 'rounded-full', 'border-b-2', 'border-blue-600', 'h-8', 'w-8')
  })

  it('renders with small size', () => {
    const { container } = render(<LoadingSpinner size="sm" />)
    
    const spinner = container.querySelector('.animate-spin')
    expect(spinner).toHaveClass('h-4', 'w-4')
  })

  it('renders with medium size (default)', () => {
    const { container } = render(<LoadingSpinner size="md" />)
    
    const spinner = container.querySelector('.animate-spin')
    expect(spinner).toHaveClass('h-8', 'w-8')
  })

  it('renders with large size', () => {
    const { container } = render(<LoadingSpinner size="lg" />)
    
    const spinner = container.querySelector('.animate-spin')
    expect(spinner).toHaveClass('h-12', 'w-12')
  })

  it('applies custom className', () => {
    const { container } = render(<LoadingSpinner className="custom-class" />)
    
    const spinnerContainer = container.firstChild as HTMLElement
    expect(spinnerContainer).toHaveClass('flex', 'items-center', 'justify-center', 'custom-class')
  })

  it('combines custom className with default classes', () => {
    const { container } = render(<LoadingSpinner className="mt-4 bg-gray-100" />)
    
    const spinnerContainer = container.firstChild as HTMLElement
    expect(spinnerContainer).toHaveClass('flex', 'items-center', 'justify-center', 'mt-4', 'bg-gray-100')
  })

  it('has proper accessibility structure', () => {
    const { container } = render(<LoadingSpinner />)
    
    const spinnerContainer = container.firstChild as HTMLElement
    const spinner = spinnerContainer.querySelector('.animate-spin')
    
    expect(spinnerContainer).toBeInTheDocument()
    expect(spinner).toBeInTheDocument()
  })

  it('maintains consistent styling across sizes', () => {
    const { rerender, container } = render(<LoadingSpinner size="sm" />)
    
    let spinner = container.querySelector('.animate-spin')
    expect(spinner).toHaveClass('animate-spin', 'rounded-full', 'border-b-2', 'border-blue-600')
    
    rerender(<LoadingSpinner size="md" />)
    spinner = container.querySelector('.animate-spin')
    expect(spinner).toHaveClass('animate-spin', 'rounded-full', 'border-b-2', 'border-blue-600')
    
    rerender(<LoadingSpinner size="lg" />)
    spinner = container.querySelector('.animate-spin')
    expect(spinner).toHaveClass('animate-spin', 'rounded-full', 'border-b-2', 'border-blue-600')
  })

  it('handles empty className prop', () => {
    const { container } = render(<LoadingSpinner className="" />)
    
    const spinnerContainer = container.firstChild as HTMLElement
    expect(spinnerContainer).toHaveClass('flex', 'items-center', 'justify-center')
  })

  it('handles undefined className prop', () => {
    const { container } = render(<LoadingSpinner className={undefined} />)
    
    const spinnerContainer = container.firstChild as HTMLElement
    expect(spinnerContainer).toHaveClass('flex', 'items-center', 'justify-center')
  })

  it('renders as a div element', () => {
    const { container } = render(<LoadingSpinner />)
    
    const spinnerContainer = container.firstChild as HTMLElement
    expect(spinnerContainer.tagName).toBe('DIV')
  })

  it('has proper CSS animation class', () => {
    const { container } = render(<LoadingSpinner />)
    
    const spinner = container.querySelector('.animate-spin')
    expect(spinner).toHaveClass('animate-spin')
  })

  it('uses consistent border styling', () => {
    const { container } = render(<LoadingSpinner />)
    
    const spinner = container.querySelector('.animate-spin')
    expect(spinner).toHaveClass('border-b-2', 'border-blue-600')
  })

  it('maintains circular shape', () => {
    const { container } = render(<LoadingSpinner />)
    
    const spinner = container.querySelector('.animate-spin')
    expect(spinner).toHaveClass('rounded-full')
  })

  it('can be used in different contexts with custom styling', () => {
    const { container } = render(
      <div className="bg-gray-900 p-4">
        <LoadingSpinner className="text-white" />
      </div>
    )
    
    const spinnerContainer = container.querySelector('.flex')
    expect(spinnerContainer).toHaveClass('text-white')
  })
})