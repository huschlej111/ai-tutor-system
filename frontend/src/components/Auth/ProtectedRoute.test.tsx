import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import ProtectedRoute from './ProtectedRoute'
import { useAuth } from '../../contexts/AuthContext'

// Mock the AuthContext
vi.mock('../../contexts/AuthContext', () => ({
  useAuth: vi.fn(),
}))

// Mock react-router-dom Navigate component
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    Navigate: ({ to }: { to: string }) => <div data-testid="navigate" data-to={to}>Navigate to {to}</div>,
  }
})

const mockUseAuth = vi.mocked(useAuth)

describe('ProtectedRoute', () => {
  const TestComponent = () => <div data-testid="protected-content">Protected Content</div>

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders children when user is authenticated', () => {
    mockUseAuth.mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
      user: { userId: '1', username: 'testuser' },
      signIn: vi.fn(),
      signUp: vi.fn(),
      signOut: vi.fn(),
      confirmSignUp: vi.fn(),
      resendConfirmationCode: vi.fn(),
      resetPassword: vi.fn(),
      confirmResetPassword: vi.fn(),
    })

    render(
      <MemoryRouter>
        <ProtectedRoute>
          <TestComponent />
        </ProtectedRoute>
      </MemoryRouter>
    )

    expect(screen.getByTestId('protected-content')).toBeInTheDocument()
    expect(screen.queryByTestId('navigate')).not.toBeInTheDocument()
  })

  it('redirects to auth page when user is not authenticated', () => {
    mockUseAuth.mockReturnValue({
      isAuthenticated: false,
      isLoading: false,
      user: null,
      signIn: vi.fn(),
      signUp: vi.fn(),
      signOut: vi.fn(),
      confirmSignUp: vi.fn(),
      resendConfirmationCode: vi.fn(),
      resetPassword: vi.fn(),
      confirmResetPassword: vi.fn(),
    })

    render(
      <MemoryRouter>
        <ProtectedRoute>
          <TestComponent />
        </ProtectedRoute>
      </MemoryRouter>
    )

    expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument()
    expect(screen.getByTestId('navigate')).toBeInTheDocument()
    expect(screen.getByTestId('navigate')).toHaveAttribute('data-to', '/auth')
  })

  it('shows loading spinner when authentication is loading', () => {
    mockUseAuth.mockReturnValue({
      isAuthenticated: false,
      isLoading: true,
      user: null,
      signIn: vi.fn(),
      signUp: vi.fn(),
      signOut: vi.fn(),
      confirmSignUp: vi.fn(),
      resendConfirmationCode: vi.fn(),
      resetPassword: vi.fn(),
      confirmResetPassword: vi.fn(),
    })

    render(
      <MemoryRouter>
        <ProtectedRoute>
          <TestComponent />
        </ProtectedRoute>
      </MemoryRouter>
    )

    expect(screen.getByText('Loading...')).toBeInTheDocument()
    expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument()
    expect(screen.queryByTestId('navigate')).not.toBeInTheDocument()
  })

  it('has proper loading state accessibility', () => {
    mockUseAuth.mockReturnValue({
      isAuthenticated: false,
      isLoading: true,
      user: null,
      signIn: vi.fn(),
      signUp: vi.fn(),
      signOut: vi.fn(),
      confirmSignUp: vi.fn(),
      resendConfirmationCode: vi.fn(),
      resetPassword: vi.fn(),
      confirmResetPassword: vi.fn(),
    })

    render(
      <MemoryRouter>
        <ProtectedRoute>
          <TestComponent />
        </ProtectedRoute>
      </MemoryRouter>
    )

    const loadingContainer = screen.getByText('Loading...').closest('div')
    expect(loadingContainer).toHaveClass('min-h-screen', 'flex', 'items-center', 'justify-center')
    
    const spinner = loadingContainer?.querySelector('.animate-spin')
    expect(spinner).toBeInTheDocument()
    expect(spinner).toHaveClass('rounded-full', 'h-8', 'w-8', 'border-b-2', 'border-primary-600')
  })

  it('renders multiple children correctly when authenticated', () => {
    mockUseAuth.mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
      user: { userId: '1', username: 'testuser' },
      signIn: vi.fn(),
      signUp: vi.fn(),
      signOut: vi.fn(),
      confirmSignUp: vi.fn(),
      resendConfirmationCode: vi.fn(),
      resetPassword: vi.fn(),
      confirmResetPassword: vi.fn(),
    })

    render(
      <MemoryRouter>
        <ProtectedRoute>
          <div data-testid="child-1">Child 1</div>
          <div data-testid="child-2">Child 2</div>
        </ProtectedRoute>
      </MemoryRouter>
    )

    expect(screen.getByTestId('child-1')).toBeInTheDocument()
    expect(screen.getByTestId('child-2')).toBeInTheDocument()
  })

  it('handles edge case when isAuthenticated is true but user is null', () => {
    mockUseAuth.mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
      user: null,
      signIn: vi.fn(),
      signUp: vi.fn(),
      signOut: vi.fn(),
      confirmSignUp: vi.fn(),
      resendConfirmationCode: vi.fn(),
      resetPassword: vi.fn(),
      confirmResetPassword: vi.fn(),
    })

    render(
      <MemoryRouter>
        <ProtectedRoute>
          <TestComponent />
        </ProtectedRoute>
      </MemoryRouter>
    )

    // Should still render children if isAuthenticated is true
    expect(screen.getByTestId('protected-content')).toBeInTheDocument()
  })

  it('handles edge case when isAuthenticated is false but user exists', () => {
    mockUseAuth.mockReturnValue({
      isAuthenticated: false,
      isLoading: false,
      user: { userId: '1', username: 'testuser' },
      signIn: vi.fn(),
      signUp: vi.fn(),
      signOut: vi.fn(),
      confirmSignUp: vi.fn(),
      resendConfirmationCode: vi.fn(),
      resetPassword: vi.fn(),
      confirmResetPassword: vi.fn(),
    })

    render(
      <MemoryRouter>
        <ProtectedRoute>
          <TestComponent />
        </ProtectedRoute>
      </MemoryRouter>
    )

    // Should redirect if isAuthenticated is false, regardless of user
    expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument()
    expect(screen.getByTestId('navigate')).toBeInTheDocument()
  })
})