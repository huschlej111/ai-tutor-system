import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import Layout from './Layout'
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
    Outlet: () => <div data-testid="outlet">Outlet</div>,
  }
})

// Mock the child components
vi.mock('./Navbar', () => ({
  default: () => <div data-testid="navbar">Navbar</div>,
}))

vi.mock('./Sidebar', () => ({
  default: () => <div data-testid="sidebar">Sidebar</div>,
}))

const mockUseAuth = vi.mocked(useAuth)

describe('Layout', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockUseAuth.mockReturnValue({
      user: { userId: '1', username: 'testuser', email: 'test@example.com' },
      signOut: vi.fn(),
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

  const renderLayout = (children?: React.ReactNode) => {
    return render(
      <MemoryRouter>
        <Layout />
      </MemoryRouter>
    )
  }

  it('renders layout with all components', () => {
    renderLayout()

    expect(screen.getByTestId('navbar')).toBeInTheDocument()
    expect(screen.getByTestId('sidebar')).toBeInTheDocument()
    expect(screen.getByRole('main')).toBeInTheDocument()
    expect(screen.getByTestId('outlet')).toBeInTheDocument()
  })

  it('has proper layout structure', () => {
    renderLayout()

    const container = screen.getByTestId('navbar').parentElement
    expect(container).toHaveClass('min-h-screen', 'bg-gray-50')

    const flexContainer = screen.getByTestId('sidebar').parentElement
    expect(flexContainer).toHaveClass('flex')

    const main = screen.getByRole('main')
    expect(main).toHaveClass('flex-1', 'p-6')
  })

  it('renders navbar at the top', () => {
    renderLayout()

    const navbar = screen.getByTestId('navbar')
    const sidebar = screen.getByTestId('sidebar')
    
    // Navbar should come before sidebar in DOM order
    expect(navbar.compareDocumentPosition(sidebar)).toBe(Node.DOCUMENT_POSITION_FOLLOWING)
  })

  it('renders sidebar and main content side by side', () => {
    renderLayout()

    const sidebar = screen.getByTestId('sidebar')
    const main = screen.getByRole('main')
    
    // Both should be in the same flex container
    expect(sidebar.parentElement).toBe(main.parentElement)
    expect(sidebar.parentElement).toHaveClass('flex')
  })

  it('has semantic HTML structure', () => {
    renderLayout()

    const main = screen.getByRole('main')
    expect(main.tagName).toBe('MAIN')
  })

  it('provides outlet for nested routes', () => {
    // The Outlet component should be rendered within the main element
    renderLayout()
    
    const main = screen.getByRole('main')
    expect(main).toBeInTheDocument()
    
    // The main element should be ready to contain routed content
    expect(main).toHaveClass('flex-1', 'p-6')
  })

  it('has proper responsive layout classes', () => {
    renderLayout()

    const container = screen.getByTestId('navbar').parentElement
    expect(container).toHaveClass('min-h-screen')

    const main = screen.getByRole('main')
    expect(main).toHaveClass('flex-1')
  })

  it('maintains consistent spacing', () => {
    renderLayout()

    const main = screen.getByRole('main')
    expect(main).toHaveClass('p-6')
  })

  it('has proper background styling', () => {
    renderLayout()

    const container = screen.getByTestId('navbar').parentElement
    expect(container).toHaveClass('bg-gray-50')
  })

  it('renders without errors when no outlet content', () => {
    expect(() => renderLayout()).not.toThrow()
  })
})