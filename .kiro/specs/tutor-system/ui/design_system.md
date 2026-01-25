# Design System: Know-It-All Tutor

## Overview

This design system provides a comprehensive library of reusable UI components, patterns, and guidelines for the Know-It-All Tutor platform. It ensures consistency, accessibility, and maintainability across all interfaces while supporting the domain-agnostic architecture.

## Design Tokens

### Color System

#### Semantic Color Mapping
```typescript
interface ColorTokens {
  // Primary Brand Colors
  primary: {
    50: '#EFF6FF',   // Lightest tint
    100: '#DBEAFE',  // Light backgrounds
    200: '#BFDBFE',  // Subtle accents
    300: '#93C5FD',  // Disabled states
    400: '#60A5FA',  // Hover states
    500: '#3B82F6',  // Default primary
    600: '#2563EB',  // Active states
    700: '#1D4ED8',  // Dark primary
    800: '#1E40AF',  // Darker contexts
    900: '#1E3A8A'   // Darkest shade
  },
  
  // Semantic Colors
  success: {
    50: '#ECFDF5',
    500: '#10B981',
    600: '#059669',
    700: '#047857'
  },
  
  warning: {
    50: '#FFFBEB',
    500: '#F59E0B',
    600: '#D97706',
    700: '#B45309'
  },
  
  error: {
    50: '#FEF2F2',
    500: '#EF4444',
    600: '#DC2626',
    700: '#B91C1C'
  },
  
  // Neutral Grays
  gray: {
    50: '#F9FAFB',   // Page backgrounds
    100: '#F3F4F6',  // Card backgrounds
    200: '#E5E7EB',  // Borders
    300: '#D1D5DB',  // Dividers
    400: '#9CA3AF',  // Placeholder text
    500: '#6B7280',  // Secondary text
    600: '#4B5563',  // Primary text
    700: '#374151',  // Headings
    800: '#1F2937',  // Dark text
    900: '#111827'   // Darkest text
  }
}
```

#### Usage Guidelines
```css
/* Correct Usage */
.button-primary {
  background-color: var(--color-primary-600);
  color: white;
}

.button-primary:hover {
  background-color: var(--color-primary-700);
}

.text-success {
  color: var(--color-success-600);
}

/* Avoid Direct Hex Values */
.incorrect {
  background-color: #2563EB; /* ❌ Don't do this */
  background-color: var(--color-primary-600); /* ✅ Do this */
}
```

### Typography Scale

#### Font Families
```css
:root {
  --font-family-primary: 'Inter', system-ui, -apple-system, sans-serif;
  --font-family-mono: 'JetBrains Mono', 'Fira Code', monospace;
  --font-family-display: 'Inter', system-ui, sans-serif;
}
```

#### Type Scale & Line Heights
```typescript
interface TypographyTokens {
  display: {
    large: { fontSize: '48px', lineHeight: '56px', fontWeight: 700 },
    medium: { fontSize: '36px', lineHeight: '44px', fontWeight: 700 },
    small: { fontSize: '30px', lineHeight: '36px', fontWeight: 600 }
  },
  
  heading: {
    h1: { fontSize: '24px', lineHeight: '32px', fontWeight: 600 },
    h2: { fontSize: '20px', lineHeight: '28px', fontWeight: 600 },
    h3: { fontSize: '18px', lineHeight: '28px', fontWeight: 600 },
    h4: { fontSize: '16px', lineHeight: '24px', fontWeight: 600 }
  },
  
  body: {
    large: { fontSize: '18px', lineHeight: '28px', fontWeight: 400 },
    medium: { fontSize: '16px', lineHeight: '24px', fontWeight: 400 },
    small: { fontSize: '14px', lineHeight: '20px', fontWeight: 400 }
  },
  
  caption: {
    large: { fontSize: '14px', lineHeight: '20px', fontWeight: 500 },
    medium: { fontSize: '12px', lineHeight: '16px', fontWeight: 500 },
    small: { fontSize: '11px', lineHeight: '16px', fontWeight: 500 }
  }
}
```

### Spacing System

#### Base Unit: 4px
```typescript
interface SpacingTokens {
  0: '0px',
  1: '4px',    // 0.25rem
  2: '8px',    // 0.5rem
  3: '12px',   // 0.75rem
  4: '16px',   // 1rem
  5: '20px',   // 1.25rem
  6: '24px',   // 1.5rem
  8: '32px',   // 2rem
  10: '40px',  // 2.5rem
  12: '48px',  // 3rem
  16: '64px',  // 4rem
  20: '80px',  // 5rem
  24: '96px'   // 6rem
}
```

#### Semantic Spacing
```css
:root {
  /* Component Internal Spacing */
  --space-component-xs: var(--space-1);  /* 4px */
  --space-component-sm: var(--space-2);  /* 8px */
  --space-component-md: var(--space-4);  /* 16px */
  --space-component-lg: var(--space-6);  /* 24px */
  
  /* Layout Spacing */
  --space-section-sm: var(--space-8);    /* 32px */
  --space-section-md: var(--space-12);   /* 48px */
  --space-section-lg: var(--space-16);   /* 64px */
  
  /* Container Spacing */
  --space-container-sm: var(--space-4);  /* 16px mobile */
  --space-container-md: var(--space-6);  /* 24px tablet */
  --space-container-lg: var(--space-8);  /* 32px desktop */
}
```

## Atomic Components

### Button Component

#### Variants & States
```typescript
interface ButtonProps {
  variant: 'primary' | 'secondary' | 'tertiary' | 'danger';
  size: 'small' | 'medium' | 'large';
  state: 'default' | 'hover' | 'active' | 'disabled' | 'loading';
  icon?: 'left' | 'right' | 'only';
  fullWidth?: boolean;
}
```

#### Implementation
```css
/* Base Button Styles */
.button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: var(--radius-md);
  font-family: var(--font-family-primary);
  font-weight: 600;
  text-decoration: none;
  cursor: pointer;
  transition: all 150ms ease-out;
  position: relative;
  overflow: hidden;
}

/* Size Variants */
.button--small {
  padding: 8px 16px;
  font-size: 14px;
  line-height: 20px;
  min-height: 36px;
}

.button--medium {
  padding: 12px 24px;
  font-size: 16px;
  line-height: 24px;
  min-height: 44px;
}

.button--large {
  padding: 16px 32px;
  font-size: 18px;
  line-height: 28px;
  min-height: 52px;
}

/* Primary Variant */
.button--primary {
  background-color: var(--color-primary-600);
  color: white;
}

.button--primary:hover {
  background-color: var(--color-primary-700);
  transform: translateY(-1px);
  box-shadow: var(--shadow-md);
}

.button--primary:active {
  background-color: var(--color-primary-800);
  transform: translateY(0);
}

.button--primary:disabled {
  background-color: var(--color-gray-300);
  color: var(--color-gray-500);
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

/* Secondary Variant */
.button--secondary {
  background-color: transparent;
  color: var(--color-primary-600);
  border: 2px solid var(--color-primary-600);
}

.button--secondary:hover {
  background-color: var(--color-primary-50);
  border-color: var(--color-primary-700);
  color: var(--color-primary-700);
}

/* Loading State */
.button--loading {
  color: transparent;
}

.button--loading::after {
  content: '';
  position: absolute;
  width: 16px;
  height: 16px;
  border: 2px solid currentColor;
  border-radius: 50%;
  border-top-color: transparent;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
```

### Input Component

#### Variants & States
```typescript
interface InputProps {
  type: 'text' | 'email' | 'password' | 'number' | 'search';
  size: 'small' | 'medium' | 'large';
  state: 'default' | 'focus' | 'error' | 'disabled';
  label?: string;
  placeholder?: string;
  helperText?: string;
  errorMessage?: string;
  icon?: 'left' | 'right';
  required?: boolean;
}
```

#### Implementation
```css
/* Input Container */
.input-group {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

/* Label */
.input-label {
  font-size: 14px;
  font-weight: 500;
  color: var(--color-gray-700);
  line-height: 20px;
}

.input-label--required::after {
  content: ' *';
  color: var(--color-error-500);
}

/* Input Field */
.input {
  width: 100%;
  border: 2px solid var(--color-gray-200);
  border-radius: var(--radius-md);
  background-color: white;
  font-family: var(--font-family-primary);
  font-size: 16px;
  line-height: 24px;
  transition: all 150ms ease-out;
}

.input--medium {
  padding: 12px 16px;
  min-height: 48px;
}

.input:focus {
  outline: none;
  border-color: var(--color-primary-600);
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
}

.input--error {
  border-color: var(--color-error-500);
}

.input--error:focus {
  border-color: var(--color-error-500);
  box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.1);
}

.input:disabled {
  background-color: var(--color-gray-50);
  color: var(--color-gray-400);
  cursor: not-allowed;
}

/* Helper Text */
.input-helper {
  font-size: 12px;
  line-height: 16px;
  color: var(--color-gray-500);
}

.input-error {
  font-size: 12px;
  line-height: 16px;
  color: var(--color-error-600);
  display: flex;
  align-items: center;
  gap: var(--space-1);
}
```

### Card Component

#### Variants & Elevations
```typescript
interface CardProps {
  variant: 'default' | 'elevated' | 'outlined' | 'interactive';
  padding: 'none' | 'small' | 'medium' | 'large';
  hover?: boolean;
  clickable?: boolean;
}
```

#### Implementation
```css
.card {
  background-color: white;
  border-radius: var(--radius-lg);
  transition: all 200ms ease-out;
}

.card--default {
  border: 1px solid var(--color-gray-200);
  box-shadow: var(--shadow-sm);
}

.card--elevated {
  border: none;
  box-shadow: var(--shadow-md);
}

.card--interactive {
  cursor: pointer;
}

.card--interactive:hover {
  box-shadow: var(--shadow-lg);
  transform: translateY(-2px);
}

.card--padding-medium {
  padding: var(--space-6);
}

.card--padding-large {
  padding: var(--space-8);
}

/* Card Header */
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-4);
}

.card-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--color-gray-800);
  line-height: 28px;
  margin: 0;
}

/* Card Content */
.card-content {
  color: var(--color-gray-600);
  line-height: 24px;
}

/* Card Footer */
.card-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: var(--space-4);
  padding-top: var(--space-4);
  border-top: 1px solid var(--color-gray-100);
}
```

### Progress Component

#### Variants
```typescript
interface ProgressProps {
  variant: 'linear' | 'circular' | 'step';
  value: number; // 0-100
  size?: 'small' | 'medium' | 'large';
  color?: 'primary' | 'success' | 'warning' | 'error';
  showLabel?: boolean;
  animated?: boolean;
}
```

#### Implementation
```css
/* Linear Progress */
.progress-linear {
  width: 100%;
  height: 8px;
  background-color: var(--color-gray-200);
  border-radius: var(--radius-sm);
  overflow: hidden;
}

.progress-linear-fill {
  height: 100%;
  background-color: var(--color-primary-600);
  border-radius: var(--radius-sm);
  transition: width 300ms ease-out;
}

.progress-linear--animated .progress-linear-fill {
  background-image: linear-gradient(
    45deg,
    rgba(255, 255, 255, 0.2) 25%,
    transparent 25%,
    transparent 50%,
    rgba(255, 255, 255, 0.2) 50%,
    rgba(255, 255, 255, 0.2) 75%,
    transparent 75%,
    transparent
  );
  background-size: 20px 20px;
  animation: progress-stripes 1s linear infinite;
}

@keyframes progress-stripes {
  0% { background-position: 0 0; }
  100% { background-position: 20px 0; }
}

/* Circular Progress */
.progress-circular {
  width: 48px;
  height: 48px;
  transform: rotate(-90deg);
}

.progress-circular-track {
  fill: none;
  stroke: var(--color-gray-200);
  stroke-width: 4;
}

.progress-circular-fill {
  fill: none;
  stroke: var(--color-primary-600);
  stroke-width: 4;
  stroke-linecap: round;
  transition: stroke-dasharray 300ms ease-out;
}
```

## Composite Components

### Quiz Question Card

#### Structure & Behavior
```typescript
interface QuizQuestionProps {
  term: string;
  questionNumber: number;
  totalQuestions: number;
  onSubmit: (answer: string) => void;
  onPause: () => void;
  onHint: () => void;
  showHint?: boolean;
  hintText?: string;
  isLoading?: boolean;
}
```

#### Implementation
```css
.quiz-question {
  max-width: 800px;
  margin: 0 auto;
  padding: var(--space-8);
}

.quiz-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-6);
}

.quiz-progress-text {
  font-size: 14px;
  color: var(--color-gray-600);
  font-weight: 500;
}

.quiz-actions {
  display: flex;
  gap: var(--space-2);
}

.quiz-term-card {
  background: linear-gradient(135deg, var(--color-primary-50) 0%, white 100%);
  border: 2px solid var(--color-primary-100);
  border-radius: var(--radius-lg);
  padding: var(--space-8);
  text-align: center;
  margin-bottom: var(--space-6);
}

.quiz-term {
  font-size: 32px;
  font-weight: 700;
  color: var(--color-primary-800);
  margin-bottom: var(--space-2);
  letter-spacing: -0.02em;
}

.quiz-prompt {
  font-size: 16px;
  color: var(--color-gray-600);
  margin: 0;
}

.quiz-answer-section {
  margin-bottom: var(--space-6);
}

.quiz-answer-label {
  display: block;
  font-size: 16px;
  font-weight: 500;
  color: var(--color-gray-700);
  margin-bottom: var(--space-3);
}

.quiz-answer-input {
  width: 100%;
  min-height: 120px;
  padding: var(--space-4);
  border: 2px solid var(--color-gray-200);
  border-radius: var(--radius-md);
  font-family: var(--font-family-primary);
  font-size: 16px;
  line-height: 24px;
  resize: vertical;
  transition: all 150ms ease-out;
}

.quiz-answer-input:focus {
  outline: none;
  border-color: var(--color-primary-600);
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
}

.quiz-submit-button {
  width: 100%;
  margin-bottom: var(--space-4);
}

.quiz-sidebar {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-4);
}

@media (max-width: 768px) {
  .quiz-sidebar {
    grid-template-columns: 1fr;
  }
}
```

### Domain Card

#### Structure & States
```typescript
interface DomainCardProps {
  domain: {
    id: string;
    name: string;
    description: string;
    difficulty: 'beginner' | 'intermediate' | 'advanced';
    termCount: number;
    progress: number; // 0-100
    subject: string;
  };
  onStart: () => void;
  onContinue: () => void;
  onDetails: () => void;
  variant: 'grid' | 'list';
}
```

#### Implementation
```css
.domain-card {
  background: white;
  border: 1px solid var(--color-gray-200);
  border-radius: var(--radius-lg);
  padding: var(--space-6);
  transition: all 200ms ease-out;
  cursor: pointer;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.domain-card:hover {
  border-color: var(--color-primary-300);
  box-shadow: var(--shadow-md);
  transform: translateY(-2px);
}

.domain-card-header {
  margin-bottom: var(--space-4);
}

.domain-card-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--color-gray-800);
  margin-bottom: var(--space-2);
  line-height: 28px;
}

.domain-card-description {
  font-size: 14px;
  color: var(--color-gray-600);
  line-height: 20px;
  margin-bottom: var(--space-3);
}

.domain-card-meta {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  margin-bottom: var(--space-4);
}

.domain-difficulty-badge {
  padding: 4px 8px;
  border-radius: var(--radius-sm);
  font-size: 12px;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.domain-difficulty-badge--beginner {
  background-color: var(--color-success-50);
  color: var(--color-success-700);
}

.domain-difficulty-badge--intermediate {
  background-color: var(--color-warning-50);
  color: var(--color-warning-700);
}

.domain-difficulty-badge--advanced {
  background-color: var(--color-error-50);
  color: var(--color-error-700);
}

.domain-term-count {
  font-size: 12px;
  color: var(--color-gray-500);
}

.domain-progress-section {
  margin-bottom: var(--space-4);
  flex-grow: 1;
}

.domain-progress-label {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-2);
}

.domain-progress-text {
  font-size: 14px;
  color: var(--color-gray-600);
  font-weight: 500;
}

.domain-progress-percentage {
  font-size: 14px;
  color: var(--color-primary-600);
  font-weight: 600;
}

.domain-card-actions {
  display: flex;
  gap: var(--space-2);
  margin-top: auto;
}

.domain-card-actions .button {
  flex: 1;
}
```

### Navigation Component

#### Structure & Responsive Behavior
```typescript
interface NavigationProps {
  user: User | null;
  currentPath: string;
  onLogout: () => void;
  notifications?: number;
}
```

#### Implementation
```css
.navigation {
  background: white;
  border-bottom: 1px solid var(--color-gray-200);
  padding: 0 var(--space-container-md);
  position: sticky;
  top: 0;
  z-index: 50;
}

.navigation-container {
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 64px;
}

.navigation-logo {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: 20px;
  font-weight: 700;
  color: var(--color-primary-600);
  text-decoration: none;
}

.navigation-menu {
  display: flex;
  align-items: center;
  gap: var(--space-6);
  list-style: none;
  margin: 0;
  padding: 0;
}

.navigation-link {
  font-size: 16px;
  font-weight: 500;
  color: var(--color-gray-600);
  text-decoration: none;
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-md);
  transition: all 150ms ease-out;
}

.navigation-link:hover {
  color: var(--color-primary-600);
  background-color: var(--color-primary-50);
}

.navigation-link--active {
  color: var(--color-primary-600);
  background-color: var(--color-primary-100);
}

.navigation-user {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.navigation-notifications {
  position: relative;
  padding: var(--space-2);
  border-radius: var(--radius-md);
  color: var(--color-gray-600);
  transition: all 150ms ease-out;
}

.navigation-notifications:hover {
  color: var(--color-primary-600);
  background-color: var(--color-primary-50);
}

.notification-badge {
  position: absolute;
  top: 4px;
  right: 4px;
  width: 8px;
  height: 8px;
  background-color: var(--color-error-500);
  border-radius: 50%;
  border: 2px solid white;
}

/* Mobile Navigation */
@media (max-width: 768px) {
  .navigation-menu {
    display: none;
  }
  
  .navigation-mobile-toggle {
    display: block;
    padding: var(--space-2);
    border: none;
    background: none;
    color: var(--color-gray-600);
    cursor: pointer;
  }
  
  .navigation-mobile-menu {
    position: absolute;
    top: 100%;
    left: 0;
    right: 0;
    background: white;
    border-bottom: 1px solid var(--color-gray-200);
    padding: var(--space-4);
    display: none;
  }
  
  .navigation-mobile-menu--open {
    display: block;
  }
  
  .navigation-mobile-menu .navigation-link {
    display: block;
    padding: var(--space-3);
    margin-bottom: var(--space-1);
  }
}
```

## Layout Components

### Container System

#### Responsive Containers
```css
.container {
  width: 100%;
  margin: 0 auto;
  padding: 0 var(--space-container-sm);
}

.container--small {
  max-width: 640px;
}

.container--medium {
  max-width: 768px;
}

.container--large {
  max-width: 1024px;
}

.container--extra-large {
  max-width: 1200px;
}

@media (min-width: 768px) {
  .container {
    padding: 0 var(--space-container-md);
  }
}

@media (min-width: 1024px) {
  .container {
    padding: 0 var(--space-container-lg);
  }
}
```

### Grid System

#### Flexible Grid Layout
```css
.grid {
  display: grid;
  gap: var(--space-6);
}

.grid--cols-1 { grid-template-columns: 1fr; }
.grid--cols-2 { grid-template-columns: repeat(2, 1fr); }
.grid--cols-3 { grid-template-columns: repeat(3, 1fr); }
.grid--cols-4 { grid-template-columns: repeat(4, 1fr); }

/* Responsive Grid */
.grid--responsive {
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
}

/* Auto-fit Grid for Cards */
.grid--auto-fit {
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
}

@media (max-width: 768px) {
  .grid--cols-2,
  .grid--cols-3,
  .grid--cols-4 {
    grid-template-columns: 1fr;
  }
}
```

## Accessibility Guidelines

### Focus Management
```css
/* Focus Styles */
.focus-visible {
  outline: 2px solid var(--color-primary-600);
  outline-offset: 2px;
}

/* Skip Links */
.skip-link {
  position: absolute;
  top: -40px;
  left: 6px;
  background: var(--color-primary-600);
  color: white;
  padding: 8px;
  text-decoration: none;
  border-radius: var(--radius-md);
  z-index: 100;
}

.skip-link:focus {
  top: 6px;
}
```

### Screen Reader Support
```css
/* Screen Reader Only Text */
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

/* High Contrast Mode */
@media (prefers-contrast: high) {
  .button--primary {
    border: 2px solid currentColor;
  }
  
  .card {
    border: 2px solid var(--color-gray-400);
  }
}

/* Reduced Motion */
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
```

## Implementation Guidelines

### CSS Architecture
```
styles/
├── tokens/
│   ├── colors.css
│   ├── typography.css
│   ├── spacing.css
│   └── shadows.css
├── base/
│   ├── reset.css
│   ├── typography.css
│   └── utilities.css
├── components/
│   ├── button.css
│   ├── input.css
│   ├── card.css
│   └── progress.css
├── layout/
│   ├── container.css
│   ├── grid.css
│   └── navigation.css
└── pages/
    ├── dashboard.css
    ├── quiz.css
    └── admin.css
```

### Component Documentation Template
```typescript
/**
 * Button Component
 * 
 * @description Primary interactive element for user actions
 * @accessibility Keyboard navigable, screen reader compatible
 * @responsive Adapts to container width when fullWidth prop is true
 * 
 * @example
 * <Button variant="primary" size="medium" onClick={handleClick}>
 *   Submit Answer
 * </Button>
 */
```

---

*This design system provides the foundation for consistent, accessible, and maintainable UI components across the Know-It-All Tutor platform, supporting both current requirements and future scalability.*