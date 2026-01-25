# User Flow Diagrams: Know-It-All Tutor System

## Overview

This document maps the complete user journeys through the Know-It-All Tutor system, focusing on decision points, error states, and "if-this-then-that" scenarios that drive the interface logic.

## Flow 1: New Student Onboarding

### Primary Path: Registration to First Quiz
```mermaid
flowchart TD
    A[Landing Page] --> B{User Account?}
    B -->|No| C[Register Page]
    B -->|Yes| D[Login Page]
    
    C --> E[Fill Registration Form]
    E --> F{Valid Data?}
    F -->|No| G[Show Validation Errors]
    G --> E
    F -->|Yes| H[Create Account]
    H --> I[Email Verification Sent]
    I --> J[Verify Email]
    J --> K[Welcome Dashboard]
    
    D --> L[Enter Credentials]
    L --> M{Valid Login?}
    M -->|No| N[Show Error Message]
    N --> L
    M -->|Yes| K
    
    K --> O[View Available Domains]
    O --> P[Select Domain]
    P --> Q[Start First Quiz]
    Q --> R[Quiz Interface]
    
    style A fill:#e1f5fe
    style K fill:#c8e6c9
    style R fill:#fff3e0
```

### Error States & Recovery
- **Invalid Email**: Inline validation with format requirements
- **Weak Password**: Real-time strength indicator with requirements
- **Email Already Exists**: Clear message with login link
- **Verification Timeout**: Resend verification option
- **Network Errors**: Retry mechanism with offline indicator

## Flow 2: Learning Session (Core User Journey)

### Quiz Taking Flow with All States
```mermaid
flowchart TD
    A[Select Domain] --> B[Quiz Configuration]
    B --> C{Resume Session?}
    C -->|Yes| D[Load Saved Progress]
    C -->|No| E[Start New Quiz]
    
    D --> F[Current Question]
    E --> F
    
    F --> G[Display Term]
    G --> H[Student Input Answer]
    H --> I[Submit Answer]
    I --> J[Evaluate Answer]
    J --> K{Correct?}
    
    K -->|Yes| L[Show Success Feedback]
    K -->|No| M[Show Correct Answer]
    
    L --> N[Update Progress]
    M --> N
    N --> O{More Questions?}
    
    O -->|Yes| P{User Action}
    O -->|No| Q[Quiz Complete]
    
    P -->|Continue| F
    P -->|Pause| R[Save Progress]
    P -->|Exit| S[Confirm Exit]
    
    R --> T[Return to Dashboard]
    S --> U{Save Progress?}
    U -->|Yes| R
    U -->|No| V[Discard Session]
    V --> T
    
    Q --> W[Show Results Summary]
    W --> X[Performance Analysis]
    X --> Y{Mastery Achieved?}
    Y -->|Yes| Z[Celebration Screen]
    Y -->|No| AA[Retry Recommendations]
    
    Z --> BB[Next Domain Suggestions]
    AA --> CC[Review Incorrect Answers]
    BB --> T
    CC --> DD[Retake Quiz Option]
    DD --> T
    
    style F fill:#fff3e0
    style L fill:#c8e6c9
    style M fill:#ffcdd2
    style Q fill:#e8f5e8
```

### Answer Evaluation Logic
```mermaid
flowchart TD
    A[Student Submits Answer] --> B[Semantic Analysis]
    B --> C[Calculate Similarity Score]
    C --> D{Score >= Threshold?}
    
    D -->|Yes| E[Mark Correct]
    D -->|No| F{Score >= Partial?}
    
    F -->|Yes| G[Partial Credit]
    F -->|No| H[Mark Incorrect]
    
    E --> I[Positive Feedback]
    G --> J[Constructive Feedback]
    H --> K[Show Correct Answer]
    
    I --> L[Update Mastery +2]
    J --> M[Update Mastery +1]
    K --> N[Update Mastery +0]
    
    L --> O[Next Question]
    M --> O
    N --> O
    
    style E fill:#c8e6c9
    style G fill:#fff9c4
    style H fill:#ffcdd2
```

## Flow 3: Content Creation Workflow

### Domain Creation Process
```mermaid
flowchart TD
    A[Create New Domain] --> B[Domain Information Form]
    B --> C[Fill Required Fields]
    C --> D{Valid Domain Data?}
    
    D -->|No| E[Show Validation Errors]
    E --> C
    D -->|Yes| F[Save Domain Draft]
    
    F --> G[Add Terms Interface]
    G --> H[Add First Term]
    H --> I[Term Definition Form]
    I --> J{Valid Term?}
    
    J -->|No| K[Show Term Errors]
    K --> I
    J -->|Yes| L[Save Term]
    
    L --> M{Add More Terms?}
    M -->|Yes| N[Add Another Term]
    M -->|No| O[Review Domain]
    
    N --> I
    O --> P{Domain Complete?}
    
    P -->|No| Q[Show Completion Requirements]
    Q --> G
    P -->|Yes| R[Publish Domain]
    
    R --> S[Domain Available for Learning]
    
    style F fill:#e3f2fd
    style L fill:#e8f5e8
    style S fill:#c8e6c9
```

### Bulk Import Flow
```mermaid
flowchart TD
    A[Bulk Import Option] --> B[Upload File Interface]
    B --> C[Select JSON File]
    C --> D[File Validation]
    D --> E{Valid Format?}
    
    E -->|No| F[Show Format Errors]
    F --> G[Download Template]
    G --> B
    
    E -->|Yes| H[Preview Import Data]
    H --> I[Show Terms Count]
    I --> J[Confirm Import]
    J --> K{User Confirms?}
    
    K -->|No| L[Cancel Import]
    K -->|Yes| M[Process Import]
    
    M --> N[Create Domain]
    N --> O[Import Terms]
    O --> P{Import Success?}
    
    P -->|No| Q[Show Import Errors]
    P -->|Yes| R[Import Complete]
    
    Q --> S[Partial Import Options]
    R --> T[Domain Available]
    
    L --> B
    S --> U{Retry Failed?}
    U -->|Yes| M
    U -->|No| T
    
    style H fill:#fff3e0
    style R fill:#c8e6c9
    style Q fill:#ffcdd2
```

## Flow 4: Progress Tracking & Analytics

### Progress Dashboard Navigation
```mermaid
flowchart TD
    A[Dashboard Home] --> B[Progress Overview]
    B --> C{View Type}
    
    C -->|Overall| D[All Domains Progress]
    C -->|Specific| E[Select Domain]
    C -->|Recent| F[Recent Activity]
    
    D --> G[Domain List with %]
    E --> H[Domain Detail View]
    F --> I[Activity Timeline]
    
    G --> J{Click Domain}
    J --> H
    
    H --> K[Term-Level Progress]
    K --> L[Mastery Indicators]
    L --> M{Action Needed?}
    
    M -->|Review| N[Review Weak Terms]
    M -->|Practice| O[Start Practice Quiz]
    M -->|Complete| P[Next Domain Suggestion]
    
    N --> Q[Focused Review Session]
    O --> R[Adaptive Quiz]
    P --> S[Domain Recommendations]
    
    I --> T[Activity Details]
    T --> U{Click Activity}
    U --> V[Resume Session]
    U --> W[View Results]
    
    style B fill:#e3f2fd
    style L fill:#fff3e0
    style Q fill:#ffcdd2
```

## Flow 5: Admin Batch Upload Process

### Administrator Content Management
```mermaid
flowchart TD
    A[Admin Login] --> B[Admin Dashboard]
    B --> C[Batch Upload Section]
    C --> D[Upload Interface]
    D --> E[Select JSON File]
    E --> F[File Upload]
    F --> G[Format Validation]
    G --> H{Valid JSON?}
    
    H -->|No| I[Show Format Errors]
    I --> J[Provide Error Details]
    J --> K[Download Correct Template]
    K --> D
    
    H -->|Yes| L[Parse Content]
    L --> M[Show Preview]
    M --> N[Display Statistics]
    N --> O[Domains: X, Terms: Y]
    O --> P[Confirm Upload]
    P --> Q{Admin Confirms?}
    
    Q -->|No| R[Cancel Upload]
    Q -->|Yes| S[Process Upload]
    
    S --> T[Create Domains]
    T --> U[Import Terms]
    U --> V[Update Database]
    V --> W{Upload Success?}
    
    W -->|No| X[Show Error Log]
    W -->|Yes| Y[Upload Complete]
    
    X --> Z[Partial Success Options]
    Y --> AA[Content Available]
    
    R --> C
    Z --> BB{Retry Failed?}
    BB -->|Yes| S
    BB -->|No| AA
    
    style L fill:#e3f2fd
    style Y fill:#c8e6c9
    style X fill:#ffcdd2
```

## Flow 6: Error Handling & Recovery

### Network Error Recovery
```mermaid
flowchart TD
    A[User Action] --> B[API Request]
    B --> C{Network Available?}
    
    C -->|No| D[Show Offline Message]
    C -->|Yes| E[Send Request]
    
    E --> F{Response OK?}
    F -->|No| G[Check Error Type]
    F -->|Yes| H[Process Response]
    
    G --> I{Retry-able Error?}
    I -->|Yes| J[Auto Retry with Backoff]
    I -->|No| K[Show Error Message]
    
    J --> L{Max Retries?}
    L -->|No| E
    L -->|Yes| K
    
    K --> M[Provide Recovery Options]
    M --> N{User Action}
    N -->|Retry| E
    N -->|Cancel| O[Return to Safe State]
    N -->|Report| P[Error Reporting]
    
    D --> Q[Queue Action for Later]
    Q --> R{Connection Restored?}
    R -->|Yes| S[Process Queued Actions]
    R -->|No| Q
    
    S --> E
    H --> T[Update UI]
    O --> U[Previous Screen]
    P --> V[Send Error Report]
    V --> U
    
    style D fill:#ffecb3
    style K fill:#ffcdd2
    style H fill:#c8e6c9
```

## Flow 7: Session Management

### Authentication & Session Handling
```mermaid
flowchart TD
    A[User Interaction] --> B[Check Auth Token]
    B --> C{Token Valid?}
    
    C -->|Yes| D[Continue Action]
    C -->|No| E{Token Expired?}
    
    E -->|Yes| F[Attempt Refresh]
    E -->|No| G[Redirect to Login]
    
    F --> H{Refresh Success?}
    H -->|Yes| I[Update Token]
    H -->|No| J[Clear Session]
    
    I --> D
    J --> G
    
    D --> K[Execute Request]
    K --> L{Auth Required?}
    L -->|No| M[Process Response]
    L -->|Yes| N{Still Authenticated?}
    
    N -->|Yes| M
    N -->|No| O[Session Expired Message]
    O --> P[Save Current State]
    P --> G
    
    G --> Q[Login Form]
    Q --> R[User Authenticates]
    R --> S{Login Success?}
    S -->|Yes| T[Restore Saved State]
    S -->|No| U[Show Login Error]
    
    T --> D
    U --> Q
    M --> V[Update UI]
    
    style C fill:#e3f2fd
    style O fill:#fff3e0
    style V fill:#c8e6c9
```

## Decision Points & Business Logic

### Quiz Difficulty Adaptation
- **High Performance (>90%)**: Suggest harder domains or advanced terms
- **Medium Performance (70-90%)**: Continue current difficulty level
- **Low Performance (<70%)**: Offer review sessions or easier content

### Progress Calculation Logic
- **Mastery Threshold**: 3 consecutive correct answers or 80% accuracy over 5 attempts
- **Retention Check**: Re-test mastered terms after 7 days
- **Adaptive Spacing**: Increase intervals for consistently correct answers

### Content Validation Rules
- **Domain Requirements**: Minimum 5 terms, maximum 100 terms per domain
- **Term Validation**: Definition must be 10-500 characters
- **Duplicate Detection**: Prevent identical terms within same domain
- **Quality Checks**: Flag domains with low engagement or high error rates

---

*These user flows provide the logical foundation for interface design, ensuring all user paths, error states, and decision points are accounted for in the UI implementation.*