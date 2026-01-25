# Technical Specifications: Know-It-All Tutor UI

## Overview

This document provides detailed technical specifications for implementing the Know-It-All Tutor user interface, including exact measurements, CSS properties, responsive breakpoints, API integration patterns, and developer handoff requirements.

## Frontend Technology Stack

### Core Technologies
```typescript
interface TechStack {
  framework: 'React 18.2+';
  language: 'TypeScript 5.0+';
  styling: 'Tailwind CSS 3.3+';
  stateManagement: 'React Context + useReducer';
  routing: 'React Router 6.8+';
  httpClient: 'Axios 1.3+';
  formHandling: 'React Hook Form 7.43+';
  testing: 'Jest + React Testing Library';
  bundler: 'Vite 4.1+';
  deployment: 'AWS S3 + CloudFront';
}
```

### Development Environment
```json
{
  "node": ">=18.0.0",
  "npm": ">=8.0.0",
  "browsers": [
    "Chrome >= 90",
    "Firefox >= 88",
    "Safari >= 14",
    "Edge >= 90"
  ]
}
```

## Responsive Design Specifications

### Breakpoint System
```css
/* Mobile First Approach */
:root {
  --breakpoint-sm: 640px;   /* Small devices */
  --breakpoint-md: 768px;   /* Medium devices */
  --breakpoint-lg: 1024px;  /* Large devices */
  --breakpoint-xl: 1280px;  /* Extra large devices */
  --breakpoint-2xl: 1536px; /* 2X large devices */
}

/* Tailwind CSS Breakpoints */
@media (min-width: 640px) { /* sm */ }
@media (min-width: 768px) { /* md */ }
@media (min-width: 1024px) { /* lg */ }
@media (min-width: 1280px) { /* xl */ }
@media (min-width: 1536px) { /* 2xl */ }
```

### Layout Specifications

#### Container Widths
```css
.container {
  width: 100%;
  margin-left: auto;
  margin-right: auto;
  padding-left: 1rem;  /* 16px */
  padding-right: 1rem; /* 16px */
}

@media (min-width: 640px) {
  .container {
    max-width: 640px;
    padding-left: 1.5rem; /* 24px */
    padding-right: 1.5rem; /* 24px */
  }
}

@media (min-width: 768px) {
  .container {
    max-width: 768px;
  }
}

@media (min-width: 1024px) {
  .container {
    max-width: 1024px;
    padding-left: 2rem; /* 32px */
    padding-right: 2rem; /* 32px */
  }
}

@media (min-width: 1280px) {
  .container {
    max-width: 1200px; /* Custom max-width */
  }
}
```

#### Grid System Implementation
```css
/* CSS Grid Layout */
.grid-responsive {
  display: grid;
  gap: 1.5rem; /* 24px */
  grid-template-columns: 1fr;
}

@media (min-width: 640px) {
  .grid-responsive {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (min-width: 1024px) {
  .grid-responsive {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (min-width: 1280px) {
  .grid-responsive {
    grid-template-columns: repeat(4, 1fr);
  }
}
```

## Component Specifications

### Button Component

#### Exact Measurements
```css
/* Small Button */
.btn-sm {
  padding: 0.5rem 1rem;     /* 8px 16px */
  font-size: 0.875rem;      /* 14px */
  line-height: 1.25rem;     /* 20px */
  min-height: 2.25rem;      /* 36px */
  border-radius: 0.5rem;    /* 8px */
}

/* Medium Button (Default) */
.btn-md {
  padding: 0.75rem 1.5rem;  /* 12px 24px */
  font-size: 1rem;          /* 16px */
  line-height: 1.5rem;      /* 24px */
  min-height: 2.75rem;      /* 44px */
  border-radius: 0.5rem;    /* 8px */
}

/* Large Button */
.btn-lg {
  padding: 1rem 2rem;       /* 16px 32px */
  font-size: 1.125rem;      /* 18px */
  line-height: 1.75rem;     /* 28px */
  min-height: 3.25rem;      /* 52px */
  border-radius: 0.5rem;    /* 8px */
}
```

#### Color Specifications
```css
/* Primary Button */
.btn-primary {
  background-color: #2563EB; /* Blue-600 */
  color: #FFFFFF;
  border: none;
  font-weight: 600;
  transition: all 150ms cubic-bezier(0.4, 0, 0.2, 1);
}

.btn-primary:hover {
  background-color: #1D4ED8; /* Blue-700 */
  transform: translateY(-1px);
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 
              0 2px 4px -1px rgba(0, 0, 0, 0.06);
}

.btn-primary:active {
  background-color: #1E40AF; /* Blue-800 */
  transform: translateY(0);
}

.btn-primary:focus {
  outline: 2px solid transparent;
  outline-offset: 2px;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.5);
}

.btn-primary:disabled {
  background-color: #D1D5DB; /* Gray-300 */
  color: #6B7280;             /* Gray-500 */
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}
```

### Input Component

#### Field Specifications
```css
.input-field {
  width: 100%;
  padding: 0.75rem 1rem;     /* 12px 16px */
  font-size: 1rem;           /* 16px */
  line-height: 1.5rem;       /* 24px */
  min-height: 3rem;          /* 48px */
  border: 2px solid #E5E7EB; /* Gray-200 */
  border-radius: 0.5rem;     /* 8px */
  background-color: #FFFFFF;
  font-family: 'Inter', system-ui, sans-serif;
  transition: all 150ms cubic-bezier(0.4, 0, 0.2, 1);
}

.input-field:focus {
  outline: none;
  border-color: #2563EB;     /* Blue-600 */
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
}

.input-field::placeholder {
  color: #9CA3AF;            /* Gray-400 */
}

.input-field:disabled {
  background-color: #F9FAFB; /* Gray-50 */
  color: #6B7280;            /* Gray-500 */
  cursor: not-allowed;
}

/* Error State */
.input-field--error {
  border-color: #DC2626;     /* Red-600 */
}

.input-field--error:focus {
  border-color: #DC2626;     /* Red-600 */
  box-shadow: 0 0 0 3px rgba(220, 38, 38, 0.1);
}
```

### Card Component

#### Layout Specifications
```css
.card {
  background-color: #FFFFFF;
  border: 1px solid #E5E7EB;  /* Gray-200 */
  border-radius: 0.75rem;     /* 12px */
  padding: 1.5rem;            /* 24px */
  box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1), 
              0 1px 2px 0 rgba(0, 0, 0, 0.06);
  transition: all 200ms cubic-bezier(0.4, 0, 0.2, 1);
}

.card:hover {
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 
              0 4px 6px -2px rgba(0, 0, 0, 0.05);
  transform: translateY(-2px);
}

.card-header {
  margin-bottom: 1rem;        /* 16px */
  padding-bottom: 1rem;       /* 16px */
  border-bottom: 1px solid #F3F4F6; /* Gray-100 */
}

.card-title {
  font-size: 1.125rem;        /* 18px */
  line-height: 1.75rem;       /* 28px */
  font-weight: 600;
  color: #1F2937;             /* Gray-800 */
  margin: 0;
}

.card-content {
  color: #4B5563;             /* Gray-600 */
  line-height: 1.5rem;        /* 24px */
}

.card-footer {
  margin-top: 1rem;           /* 16px */
  padding-top: 1rem;          /* 16px */
  border-top: 1px solid #F3F4F6; /* Gray-100 */
  display: flex;
  justify-content: space-between;
  align-items: center;
}
```

## Page Layout Specifications

### Dashboard Layout
```css
.dashboard-layout {
  display: grid;
  grid-template-areas: 
    "header header"
    "sidebar main"
    "footer footer";
  grid-template-columns: 280px 1fr;
  grid-template-rows: auto 1fr auto;
  min-height: 100vh;
  gap: 0;
}

.dashboard-header {
  grid-area: header;
  height: 4rem;               /* 64px */
  border-bottom: 1px solid #E5E7EB;
  background-color: #FFFFFF;
  position: sticky;
  top: 0;
  z-index: 40;
}

.dashboard-sidebar {
  grid-area: sidebar;
  background-color: #F9FAFB;  /* Gray-50 */
  border-right: 1px solid #E5E7EB;
  padding: 1.5rem;            /* 24px */
  overflow-y: auto;
}

.dashboard-main {
  grid-area: main;
  padding: 2rem;              /* 32px */
  overflow-y: auto;
}

/* Mobile Layout */
@media (max-width: 768px) {
  .dashboard-layout {
    grid-template-areas: 
      "header"
      "main"
      "footer";
    grid-template-columns: 1fr;
  }
  
  .dashboard-sidebar {
    display: none;
  }
  
  .dashboard-main {
    padding: 1rem;            /* 16px */
  }
}
```

### Quiz Interface Layout
```css
.quiz-layout {
  max-width: 800px;
  margin: 0 auto;
  padding: 2rem 1rem;         /* 32px 16px */
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.quiz-header {
  margin-bottom: 2rem;        /* 32px */
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.quiz-progress {
  width: 100%;
  height: 0.5rem;             /* 8px */
  background-color: #E5E7EB;  /* Gray-200 */
  border-radius: 0.25rem;     /* 4px */
  margin-bottom: 1rem;        /* 16px */
  overflow: hidden;
}

.quiz-progress-fill {
  height: 100%;
  background-color: #10B981;  /* Green-500 */
  border-radius: 0.25rem;     /* 4px */
  transition: width 300ms ease-out;
}

.quiz-question-card {
  background: linear-gradient(135deg, #EFF6FF 0%, #FFFFFF 100%);
  border: 2px solid #DBEAFE;  /* Blue-100 */
  border-radius: 0.75rem;     /* 12px */
  padding: 3rem 2rem;         /* 48px 32px */
  text-align: center;
  margin-bottom: 2rem;        /* 32px */
}

.quiz-term {
  font-size: 2rem;            /* 32px */
  line-height: 2.5rem;        /* 40px */
  font-weight: 700;
  color: #1E40AF;             /* Blue-800 */
  margin-bottom: 0.5rem;      /* 8px */
  letter-spacing: -0.02em;
}

.quiz-answer-section {
  margin-bottom: 2rem;        /* 32px */
  flex-grow: 1;
}

.quiz-answer-textarea {
  width: 100%;
  min-height: 7.5rem;         /* 120px */
  padding: 1rem;              /* 16px */
  border: 2px solid #E5E7EB;  /* Gray-200 */
  border-radius: 0.5rem;      /* 8px */
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 1rem;            /* 16px */
  line-height: 1.5rem;        /* 24px */
  resize: vertical;
  transition: all 150ms ease-out;
}

.quiz-sidebar {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;                  /* 16px */
  margin-bottom: 2rem;        /* 32px */
}

@media (max-width: 640px) {
  .quiz-layout {
    padding: 1rem 0.5rem;     /* 16px 8px */
  }
  
  .quiz-question-card {
    padding: 2rem 1rem;       /* 32px 16px */
  }
  
  .quiz-term {
    font-size: 1.5rem;        /* 24px */
    line-height: 2rem;        /* 32px */
  }
  
  .quiz-sidebar {
    grid-template-columns: 1fr;
  }
}
```

## API Integration Specifications

### HTTP Client Configuration
```typescript
// axios.config.ts
import axios, { AxiosRequestConfig, AxiosResponse } from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'https://api.know-it-all-tutor.com';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for auth token
apiClient.interceptors.request.use(
  (config: AxiosRequestConfig) => {
    const token = localStorage.getItem('authToken');
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response: AxiosResponse) => response,
  async (error) => {
    if (error.response?.status === 401) {
      // Handle token refresh or redirect to login
      localStorage.removeItem('authToken');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);
```

### API Endpoint Specifications
```typescript
// api/endpoints.ts
export const API_ENDPOINTS = {
  // Authentication
  AUTH: {
    LOGIN: '/auth/login',
    REGISTER: '/auth/register',
    REFRESH: '/auth/refresh',
    LOGOUT: '/auth/logout',
  },
  
  // Domains
  DOMAINS: {
    LIST: '/domains',
    CREATE: '/domains',
    GET: (id: string) => `/domains/${id}`,
    UPDATE: (id: string) => `/domains/${id}`,
    DELETE: (id: string) => `/domains/${id}`,
  },
  
  // Quiz
  QUIZ: {
    START: '/quiz/start',
    SUBMIT_ANSWER: '/quiz/answer',
    PAUSE: '/quiz/pause',
    RESUME: (sessionId: string) => `/quiz/resume/${sessionId}`,
    COMPLETE: (sessionId: string) => `/quiz/complete/${sessionId}`,
  },
  
  // Progress
  PROGRESS: {
    GET: '/progress',
    GET_DOMAIN: (domainId: string) => `/progress/domain/${domainId}`,
    DASHBOARD: '/progress/dashboard',
  },
  
  // Admin
  ADMIN: {
    BATCH_UPLOAD: '/admin/batch-upload',
    VALIDATE_FILE: '/admin/validate-file',
    UPLOAD_HISTORY: '/admin/upload-history',
  },
} as const;
```

### Request/Response Type Definitions
```typescript
// types/api.ts

// Authentication Types
export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  token: string;
  refreshToken: string;
  user: {
    id: string;
    email: string;
    username: string;
  };
}

export interface RegisterRequest {
  username: string;
  email: string;
  password: string;
}

// Domain Types
export interface Domain {
  id: string;
  name: string;
  description: string;
  subject: string;
  difficulty: 'beginner' | 'intermediate' | 'advanced';
  termCount: number;
  progress: number;
  createdAt: string;
  updatedAt: string;
}

export interface CreateDomainRequest {
  name: string;
  description: string;
  subject: string;
  difficulty: 'beginner' | 'intermediate' | 'advanced';
  estimatedHours?: number;
  prerequisites?: string[];
  tags?: string[];
}

// Quiz Types
export interface StartQuizRequest {
  domainId: string;
}

export interface StartQuizResponse {
  sessionId: string;
  domainName: string;
  totalQuestions: number;
  currentQuestion: {
    id: string;
    term: string;
    questionNumber: number;
  };
}

export interface SubmitAnswerRequest {
  sessionId: string;
  questionId: string;
  answer: string;
}

export interface SubmitAnswerResponse {
  isCorrect: boolean;
  similarityScore: number;
  feedback: string;
  correctDefinition: string;
  nextQuestion?: {
    id: string;
    term: string;
    questionNumber: number;
  };
  isComplete: boolean;
}

// Progress Types
export interface ProgressDashboard {
  overallProgress: number;
  totalDomains: number;
  completedDomains: number;
  totalTermsMastered: number;
  studyStreak: number;
  recentActivity: ActivityItem[];
  domainProgress: DomainProgress[];
}

export interface DomainProgress {
  domainId: string;
  domainName: string;
  progress: number;
  totalTerms: number;
  masteredTerms: number;
  averageScore: number;
}

// Error Types
export interface ApiError {
  code: string;
  message: string;
  details?: Record<string, any>;
  timestamp: string;
  requestId: string;
}
```

### Error Handling Patterns
```typescript
// hooks/useApiError.ts
import { useState } from 'react';
import { ApiError } from '../types/api';

export const useApiError = () => {
  const [error, setError] = useState<ApiError | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleApiCall = async <T>(
    apiCall: () => Promise<T>
  ): Promise<T | null> => {
    try {
      setIsLoading(true);
      setError(null);
      const result = await apiCall();
      return result;
    } catch (err: any) {
      const apiError: ApiError = {
        code: err.response?.data?.error?.code || 'UNKNOWN_ERROR',
        message: err.response?.data?.error?.message || 'An unexpected error occurred',
        details: err.response?.data?.error?.details,
        timestamp: new Date().toISOString(),
        requestId: err.response?.headers?.['x-request-id'] || 'unknown',
      };
      setError(apiError);
      return null;
    } finally {
      setIsLoading(false);
    }
  };

  const clearError = () => setError(null);

  return { error, isLoading, handleApiCall, clearError };
};
```

## State Management Specifications

### Context Structure
```typescript
// context/AppContext.tsx
import React, { createContext, useContext, useReducer, ReactNode } from 'react';

interface User {
  id: string;
  email: string;
  username: string;
}

interface AppState {
  user: User | null;
  isAuthenticated: boolean;
  currentDomain: Domain | null;
  quizSession: QuizSession | null;
  notifications: Notification[];
  theme: 'light' | 'dark';
  sidebarOpen: boolean;
}

type AppAction =
  | { type: 'SET_USER'; payload: User }
  | { type: 'LOGOUT' }
  | { type: 'SET_CURRENT_DOMAIN'; payload: Domain }
  | { type: 'START_QUIZ_SESSION'; payload: QuizSession }
  | { type: 'END_QUIZ_SESSION' }
  | { type: 'ADD_NOTIFICATION'; payload: Notification }
  | { type: 'REMOVE_NOTIFICATION'; payload: string }
  | { type: 'TOGGLE_SIDEBAR' }
  | { type: 'SET_THEME'; payload: 'light' | 'dark' };

const initialState: AppState = {
  user: null,
  isAuthenticated: false,
  currentDomain: null,
  quizSession: null,
  notifications: [],
  theme: 'light',
  sidebarOpen: false,
};

const appReducer = (state: AppState, action: AppAction): AppState => {
  switch (action.type) {
    case 'SET_USER':
      return {
        ...state,
        user: action.payload,
        isAuthenticated: true,
      };
    
    case 'LOGOUT':
      return {
        ...state,
        user: null,
        isAuthenticated: false,
        currentDomain: null,
        quizSession: null,
      };
    
    case 'SET_CURRENT_DOMAIN':
      return {
        ...state,
        currentDomain: action.payload,
      };
    
    case 'START_QUIZ_SESSION':
      return {
        ...state,
        quizSession: action.payload,
      };
    
    case 'END_QUIZ_SESSION':
      return {
        ...state,
        quizSession: null,
      };
    
    case 'ADD_NOTIFICATION':
      return {
        ...state,
        notifications: [...state.notifications, action.payload],
      };
    
    case 'REMOVE_NOTIFICATION':
      return {
        ...state,
        notifications: state.notifications.filter(n => n.id !== action.payload),
      };
    
    case 'TOGGLE_SIDEBAR':
      return {
        ...state,
        sidebarOpen: !state.sidebarOpen,
      };
    
    case 'SET_THEME':
      return {
        ...state,
        theme: action.payload,
      };
    
    default:
      return state;
  }
};

const AppContext = createContext<{
  state: AppState;
  dispatch: React.Dispatch<AppAction>;
} | null>(null);

export const AppProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [state, dispatch] = useReducer(appReducer, initialState);

  return (
    <AppContext.Provider value={{ state, dispatch }}>
      {children}
    </AppContext.Provider>
  );
};

export const useAppContext = () => {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useAppContext must be used within an AppProvider');
  }
  return context;
};
```

## Performance Specifications

### Bundle Size Targets
```typescript
interface PerformanceTargets {
  initialBundle: '< 250KB gzipped';
  chunkSize: '< 100KB per route chunk';
  imageOptimization: 'WebP format, lazy loading';
  fontLoading: 'font-display: swap';
  cacheStrategy: 'Service worker for static assets';
}
```

### Code Splitting Strategy
```typescript
// Lazy loading for route components
import { lazy, Suspense } from 'react';

const Dashboard = lazy(() => import('../pages/Dashboard'));
const QuizInterface = lazy(() => import('../pages/QuizInterface'));
const ContentCreation = lazy(() => import('../pages/ContentCreation'));
const AdminPanel = lazy(() => import('../pages/AdminPanel'));

// Route configuration with lazy loading
export const routes = [
  {
    path: '/dashboard',
    element: (
      <Suspense fallback={<LoadingSpinner />}>
        <Dashboard />
      </Suspense>
    ),
  },
  {
    path: '/learn/quiz/:domainId',
    element: (
      <Suspense fallback={<LoadingSpinner />}>
        <QuizInterface />
      </Suspense>
    ),
  },
  // ... other routes
];
```

### Optimization Guidelines
```typescript
// Image optimization
const OptimizedImage: React.FC<{
  src: string;
  alt: string;
  width: number;
  height: number;
}> = ({ src, alt, width, height }) => (
  <img
    src={src}
    alt={alt}
    width={width}
    height={height}
    loading="lazy"
    decoding="async"
    style={{ aspectRatio: `${width}/${height}` }}
  />
);

// Memoization for expensive calculations
const ExpensiveComponent = React.memo(({ data }: { data: any[] }) => {
  const processedData = useMemo(() => {
    return data.map(item => expensiveCalculation(item));
  }, [data]);

  return <div>{/* Render processed data */}</div>;
});
```

## Accessibility Implementation

### ARIA Specifications
```typescript
// Screen reader announcements
const useAnnouncement = () => {
  const announce = (message: string, priority: 'polite' | 'assertive' = 'polite') => {
    const announcement = document.createElement('div');
    announcement.setAttribute('aria-live', priority);
    announcement.setAttribute('aria-atomic', 'true');
    announcement.className = 'sr-only';
    announcement.textContent = message;
    
    document.body.appendChild(announcement);
    
    setTimeout(() => {
      document.body.removeChild(announcement);
    }, 1000);
  };

  return { announce };
};

// Focus management
const useFocusManagement = () => {
  const focusElement = (selector: string) => {
    const element = document.querySelector(selector) as HTMLElement;
    if (element) {
      element.focus();
    }
  };

  const trapFocus = (containerRef: React.RefObject<HTMLElement>) => {
    // Implementation for focus trapping in modals
  };

  return { focusElement, trapFocus };
};
```

### Keyboard Navigation
```css
/* Focus indicators */
.focus-visible {
  outline: 2px solid #2563EB;
  outline-offset: 2px;
  border-radius: 0.25rem;
}

/* Skip links */
.skip-link {
  position: absolute;
  top: -40px;
  left: 6px;
  background: #2563EB;
  color: white;
  padding: 8px;
  text-decoration: none;
  border-radius: 4px;
  z-index: 100;
  transition: top 0.3s;
}

.skip-link:focus {
  top: 6px;
}

/* High contrast mode support */
@media (prefers-contrast: high) {
  .button {
    border: 2px solid currentColor;
  }
  
  .card {
    border: 2px solid #4B5563;
  }
}

/* Reduced motion support */
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}
```

## Testing Specifications

### Unit Testing Requirements
```typescript
// Component testing example
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { Button } from '../Button';

describe('Button Component', () => {
  it('renders with correct text', () => {
    render(<Button>Click me</Button>);
    expect(screen.getByRole('button', { name: 'Click me' })).toBeInTheDocument();
  });

  it('calls onClick handler when clicked', () => {
    const handleClick = jest.fn();
    render(<Button onClick={handleClick}>Click me</Button>);
    
    fireEvent.click(screen.getByRole('button'));
    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  it('shows loading state correctly', () => {
    render(<Button loading>Submit</Button>);
    expect(screen.getByRole('button')).toHaveAttribute('aria-busy', 'true');
  });

  it('is accessible via keyboard', () => {
    render(<Button>Click me</Button>);
    const button = screen.getByRole('button');
    
    button.focus();
    expect(button).toHaveFocus();
    
    fireEvent.keyDown(button, { key: 'Enter' });
    // Assert expected behavior
  });
});
```

### Integration Testing
```typescript
// API integration testing
import { rest } from 'msw';
import { setupServer } from 'msw/node';
import { render, screen, waitFor } from '@testing-library/react';
import { QuizInterface } from '../QuizInterface';

const server = setupServer(
  rest.post('/api/quiz/start', (req, res, ctx) => {
    return res(ctx.json({
      sessionId: 'test-session',
      domainName: 'Test Domain',
      totalQuestions: 10,
      currentQuestion: {
        id: 'q1',
        term: 'Lambda',
        questionNumber: 1,
      },
    }));
  })
);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

test('starts quiz and displays first question', async () => {
  render(<QuizInterface domainId="test-domain" />);
  
  await waitFor(() => {
    expect(screen.getByText('Lambda')).toBeInTheDocument();
    expect(screen.getByText('Question 1 of 10')).toBeInTheDocument();
  });
});
```

## Deployment Specifications

### Build Configuration
```typescript
// vite.config.ts
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { resolve } from 'path';

export default defineConfig({
  plugins: [react()],
  build: {
    outDir: 'dist',
    sourcemap: true,
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom'],
          router: ['react-router-dom'],
          ui: ['@headlessui/react', '@heroicons/react'],
        },
      },
    },
  },
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
      '@components': resolve(__dirname, 'src/components'),
      '@pages': resolve(__dirname, 'src/pages'),
      '@hooks': resolve(__dirname, 'src/hooks'),
      '@utils': resolve(__dirname, 'src/utils'),
      '@types': resolve(__dirname, 'src/types'),
    },
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
});
```

### AWS S3 + CloudFront Deployment
```yaml
# deploy.yml (GitHub Actions)
name: Deploy to AWS S3

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'
          cache: 'npm'
      
      - name: Install dependencies
        run: npm ci
      
      - name: Run tests
        run: npm run test:ci
      
      - name: Build application
        run: npm run build
        env:
          REACT_APP_API_BASE_URL: ${{ secrets.API_BASE_URL }}
      
      - name: Deploy to S3
        run: |
          aws s3 sync dist/ s3://${{ secrets.S3_BUCKET }} --delete
          aws cloudfront create-invalidation --distribution-id ${{ secrets.CLOUDFRONT_DISTRIBUTION_ID }} --paths "/*"
        env:
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          AWS_DEFAULT_REGION: us-east-1
```

---

*These technical specifications provide the detailed implementation guidelines needed for developers to build the Know-It-All Tutor interface according to the established design system and architectural requirements.*