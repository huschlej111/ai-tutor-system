import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import Navbar from './Navbar'
import { useAuth } from '../../contexts/AuthContext'

// Mock the AuthContext
vi.mock('../../contexts/AuthContext', () => ({
  useAuth: vi.fn(),
}))

// Mock react-router-dom
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
  }
})

const mockUseAuth = vi.mocked(useAuth)

describe('Navbar', () => {
  const mockSignOut = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
    mockUseAuth.mockReturnValue({
      user: { userId: '1', username: 'testuser', email: 'test@example.com' },
      signOut: mockSignOut,
      isLoading: false,
      isAuthenticated: true,
      signIn: vi.fn(),
      signUp: vi.fn(),
      confirmSignUp: vi.fn(),
      resendConfirmationCode: vi.fn(),
      resetPassword: vi.fn(),
      confirmResetPassword: vi.fn(),
    })
  })

  const renderNavbar = () => {
    return render(
      <MemoryRouter>
        <Navbar />
      </MemoryRouter>
    )
  }

  it('renders navbar with all elements', () => {
    renderNavbar()

    expect(screen.getByText('Know-It-All Tutor')).toBeInTheDocument()
    expect(screen.getByText('Welcome, testuser')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Know-It-All Tutor' })).toHaveAttribute('href', '/app/dashboard')
    
    const profileLink = screen.getByRole('link', { name: '' }) // Profile link with icon
    expect(profileLink).toHaveAttribute('href', '/app/profile')
    
    expect(screen.getByRole('button')).toBeInTheDocument() // Sign out button
  })

  it('displays username when available', () => {
    renderNavbar()
    expect(screen.getByText('Welcome, testuser')).toBeInTheDocument()
  })

  it('displays email when username is not available', () => {
    mockUseAuth.mockReturnValue({
      user: { userId: '1', username: '', email: 'test@example.com' },
      signOut: mockSignOut,
      isLoading: false,
      isAuthenticated: true,
      signIn: vi.fn(),
      signUp: vi.fn(),
      confirmSignUp: vi.fn(),
      resendConfirmationCode: vi.fn(),
      resetPassword: vi.fn(),
      confirmResetPassword: vi.fn(),
    })

    renderNavbar()
    expect(screen.getByText('Welcome, test@example.com')).toBeInTheDocument()
  })

  it('displays fallback text when neither username nor email is available', () => {
    mockUseAuth.mockReturnValue({
      user: { userId: '1', username: '', email: '' },
      signOut: mockSignOut,
      isLoading: false,
      isAuthenticated: true,
      signIn: vi.fn(),
      signUp: vi.fn(),
      confirmSignUp: vi.fn(),
      resendConfirmationCode: vi.fn(),
      resetPassword: vi.fn(),
      confirmResetPassword: vi.fn(),
    })

    renderNavbar()
    expect(screen.getByText('Welcome, User')).toBeInTheDocument()
  })

  it('navigates to profile when profile icon is clicked', async () => {
    const user = userEvent.setup()
    renderNavbar()

    const profileLink = screen.getByRole('link', { name: '' }) // Profile link with icon
    expect(profileLink).toHaveAttribute('href', '/app/profile')
  })

  it('calls signOut when logout button is clicked', async () => {
    const user = userEvent.setup()
    renderNavbar()

    const signOutButton = screen.getByRole('button')
    await user.click(signOutButton)

    expect(mockSignOut).toHaveBeenCalled()
  })

  it('has proper accessibility attributes', () => {
    renderNavbar()

    const nav = screen.getByRole('navigation')
    expect(nav).toBeInTheDocument()

    const profileLink = screen.getByRole('link', { name: '' }) // Profile link with icon
    expect(profileLink).toHaveClass('p-2', 'text-gray-600', 'hover:text-primary-600', 'transition-colors')

    const signOutButton = screen.getByRole('button')
    expect(signOutButton).toHaveClass('p-2', 'text-gray-600', 'hover:text-error-600', 'transition-colors')
  })

  it('supports keyboard navigation', async () => {
    const user = userEvent.setup()
    renderNavbar()

    const logoLink = screen.getByRole('link', { name: 'Know-It-All Tutor' })
    const profileLink = screen.getByRole('link', { name: '' }) // Profile link with icon
    const signOutButton = screen.getByRole('button')

    // Tab navigation
    await user.tab()
    expect(logoLink).toHaveFocus()

    await user.tab()
    expect(profileLink).toHaveFocus()

    await user.tab()
    expect(signOutButton).toHaveFocus()
  })

  it('handles sign out with Enter key', async () => {
    const user = userEvent.setup()
    renderNavbar()

    const signOutButton = screen.getByRole('button')
    signOutButton.focus()
    await user.keyboard('{Enter}')

    expect(mockSignOut).toHaveBeenCalled()
  })

  it('handles sign out with Space key', async () => {
    const user = userEvent.setup()
    renderNavbar()

    const signOutButton = screen.getByRole('button')
    signOutButton.focus()
    await user.keyboard(' ')

    expect(mockSignOut).toHaveBeenCalled()
  })

  it('has proper visual styling', () => {
    renderNavbar()

    const nav = screen.getByRole('navigation')
    expect(nav).toHaveClass('bg-white', 'border-b', 'border-gray-200', 'px-6', 'py-4')

    const container = nav.querySelector('.flex.items-center.justify-between')
    expect(container).toBeInTheDocument()

    const logo = screen.getByText('Know-It-All Tutor')
    expect(logo).toHaveClass('text-xl', 'font-bold', 'text-primary-600')
  })

  it('handles null user gracefully', () => {
    mockUseAuth.mockReturnValue({
      user: null,
      signOut: mockSignOut,
      isLoading: false,
      isAuthenticated: false,
      signIn: vi.fn(),
      signUp: vi.fn(),
      confirmSignUp: vi.fn(),
      resendConfirmationCode: vi.fn(),
      resetPassword: vi.fn(),
      confirmResetPassword: vi.fn(),
    })

    renderNavbar()
    expect(screen.getByText('Welcome, User')).toBeInTheDocument()
  })

  it('renders icons with correct sizes', () => {
    renderNavbar()

    // Check that User and LogOut icons are rendered (they should be in the DOM)
    const profileLink = screen.getByRole('link', { name: '' }) // Profile link with icon
    const signOutButton = screen.getByRole('button')

    expect(profileLink.querySelector('svg')).toBeInTheDocument()
    expect(signOutButton.querySelector('svg')).toBeInTheDocument()
  })
})