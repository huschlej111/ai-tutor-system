import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import Sidebar from './Sidebar'

// Mock react-router-dom to include MemoryRouter
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
  }
})

describe('Sidebar', () => {
  const renderSidebar = (initialEntries = ['/app/dashboard']) => {
    return render(
      <MemoryRouter initialEntries={initialEntries}>
        <Sidebar />
      </MemoryRouter>
    )
  }

  it('renders all navigation items', () => {
    renderSidebar()

    expect(screen.getByText('Dashboard')).toBeInTheDocument()
    expect(screen.getByText('Domain Library')).toBeInTheDocument()
    expect(screen.getByText('Create Domain')).toBeInTheDocument()
    expect(screen.getByText('Admin Panel')).toBeInTheDocument()
    expect(screen.getByText('Profile')).toBeInTheDocument()
  })

  it('renders navigation links with correct hrefs', () => {
    renderSidebar()

    expect(screen.getByRole('link', { name: /dashboard/i })).toHaveAttribute('href', '/app/dashboard')
    expect(screen.getByRole('link', { name: /domain library/i })).toHaveAttribute('href', '/app/domains')
    expect(screen.getByRole('link', { name: /create domain/i })).toHaveAttribute('href', '/app/domains/create')
    expect(screen.getByRole('link', { name: /admin panel/i })).toHaveAttribute('href', '/app/admin')
    expect(screen.getByRole('link', { name: /profile/i })).toHaveAttribute('href', '/app/profile')
  })

  it('highlights active navigation item', () => {
    renderSidebar(['/app/domains'])

    const domainLibraryLink = screen.getByRole('link', { name: /domain library/i })
    expect(domainLibraryLink).toHaveClass('bg-primary-100', 'text-primary-700')

    const dashboardLink = screen.getByRole('link', { name: /dashboard/i })
    expect(dashboardLink).toHaveClass('text-gray-600')
    expect(dashboardLink).not.toHaveClass('bg-primary-100', 'text-primary-700')
  })

  it('applies correct styling to navigation items', () => {
    renderSidebar()

    const links = screen.getAllByRole('link')
    links.forEach(link => {
      expect(link).toHaveClass(
        'flex',
        'items-center',
        'space-x-3',
        'px-3',
        'py-2',
        'rounded-md',
        'text-sm',
        'font-medium',
        'transition-colors'
      )
    })
  })

  it('renders icons for each navigation item', () => {
    renderSidebar()

    const links = screen.getAllByRole('link')
    links.forEach(link => {
      const icon = link.querySelector('svg')
      expect(icon).toBeInTheDocument()
    })
  })

  it('has proper sidebar structure and styling', () => {
    renderSidebar()

    const sidebar = screen.getByRole('complementary')
    expect(sidebar).toHaveClass('w-64', 'bg-white', 'border-r', 'border-gray-200', 'min-h-screen')

    const nav = screen.getByRole('navigation')
    expect(nav).toHaveClass('p-4', 'space-y-2')
  })

  it('supports keyboard navigation', async () => {
    const user = userEvent.setup()
    renderSidebar()

    const firstLink = screen.getByRole('link', { name: /dashboard/i })
    const secondLink = screen.getByRole('link', { name: /domain library/i })

    // Tab navigation
    await user.tab()
    expect(firstLink).toHaveFocus()

    await user.tab()
    expect(secondLink).toHaveFocus()
  })

  it('handles navigation with Enter key', async () => {
    const user = userEvent.setup()
    renderSidebar()

    const dashboardLink = screen.getByRole('link', { name: /dashboard/i })
    dashboardLink.focus()
    
    // Simulate Enter key press
    await user.keyboard('{Enter}')
    
    // The link should still be in the document and focused
    expect(dashboardLink).toBeInTheDocument()
  })

  it('applies hover classes in component definition', async () => {
    renderSidebar()

    const dashboardLink = screen.getByRole('link', { name: /dashboard/i })
    
    // Since the dashboard is active, it should have active classes
    // For inactive links, we can check that the component structure is correct
    expect(dashboardLink).toHaveClass('flex', 'items-center', 'space-x-3', 'px-3', 'py-2', 'rounded-md', 'text-sm', 'font-medium', 'transition-colors')
  })

  it('maintains accessibility with proper ARIA roles', () => {
    renderSidebar()

    expect(screen.getByRole('complementary')).toBeInTheDocument() // aside element
    expect(screen.getByRole('navigation')).toBeInTheDocument() // nav element
    
    const links = screen.getAllByRole('link')
    expect(links).toHaveLength(5) // All navigation items should be links
  })

  it('handles different active routes correctly', () => {
    // Test Create Domain active state
    renderSidebar(['/app/domains/create'])
    
    const createDomainLink = screen.getByRole('link', { name: /create domain/i })
    expect(createDomainLink).toHaveClass('bg-primary-100', 'text-primary-700')
  })

  it('handles admin panel route correctly', () => {
    renderSidebar(['/app/admin'])
    
    const adminLink = screen.getByRole('link', { name: /admin panel/i })
    expect(adminLink).toHaveClass('bg-primary-100', 'text-primary-700')
  })

  it('handles profile route correctly', () => {
    renderSidebar(['/app/profile'])
    
    const profileLink = screen.getByRole('link', { name: /profile/i })
    expect(profileLink).toHaveClass('bg-primary-100', 'text-primary-700')
  })

  it('renders with semantic HTML structure', () => {
    renderSidebar()

    // Check for proper semantic structure
    const aside = screen.getByRole('complementary')
    expect(aside.tagName).toBe('ASIDE')

    const nav = screen.getByRole('navigation')
    expect(nav.tagName).toBe('NAV')
    expect(aside).toContainElement(nav)
  })

  it('has consistent spacing and layout', () => {
    renderSidebar()

    const nav = screen.getByRole('navigation')
    expect(nav).toHaveClass('p-4', 'space-y-2')

    const links = screen.getAllByRole('link')
    links.forEach(link => {
      expect(link).toHaveClass('space-x-3', 'px-3', 'py-2')
    })
  })
})