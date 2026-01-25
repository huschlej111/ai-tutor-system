# Requirements Document

## Introduction

The Know-It-All Tutor system is a web-based learning platform that transforms terminology-heavy subjects into interactive, hands-on tutorials. The system enables students to master complex vocabularies through guided quizzes and progressive learning, with initial focus on AWS certification and Python programming concepts.

## Glossary

- **System**: The Know-It-All Tutor web application
- **Student**: A user who takes quizzes and learns terminology
- **Knowledge_Domain**: A collection of terms and definitions for a specific subject area
- **Quiz**: An interactive learning session where students are tested on terminology
- **Tutorial**: A guided learning experience through a knowledge domain
- **Progress**: A student's completion status and performance metrics within knowledge domains
- **Administrator**: A user with privileges to manage content and moderate submissions

## Requirements

### Requirement 1: User Authentication with AWS Cognito

**User Story:** As a student, I want to create an account and log in using AWS Cognito, so that I can access personalized learning content with enterprise-grade security and additional authentication features.

#### Acceptance Criteria

1. WHEN a new user visits the registration page, THE System SHALL provide fields for username, email, and password and integrate with AWS Cognito User Pool for account creation
2. WHEN a user submits valid registration information, THE System SHALL create a new account in Cognito, send email verification, and redirect to email confirmation page
3. WHEN a user attempts to register with an existing email, THE System SHALL prevent registration using Cognito's built-in duplicate prevention and display an appropriate error message
4. WHEN a registered user enters correct login credentials, THE System SHALL authenticate them through Cognito and grant access to their dashboard using Cognito JWT tokens
5. WHEN a user enters incorrect login credentials, THE System SHALL reject the login attempt using Cognito authentication and display an error message
6. WHEN an authenticated user logs out, THE System SHALL terminate their Cognito session and redirect to the login page
7. WHEN a user requests password reset, THE System SHALL use Cognito's forgot password flow to send reset instructions via email
8. WHEN a user wants to verify their email, THE System SHALL use Cognito's email verification process
9. WHEN multi-factor authentication is enabled, THE System SHALL support TOTP and SMS-based MFA through Cognito

### Requirement 2: Knowledge Domain Management

**User Story:** As a student, I want to add knowledge domains to the system, so that I can create custom learning content for my specific needs.

#### Acceptance Criteria

1. WHEN a student accesses the content creation interface, THE System SHALL provide fields to define a new knowledge domain with name and description
2. WHEN a student adds terms to a knowledge domain, THE System SHALL store each term with its definition and associate it with the domain
3. WHEN a student submits a complete knowledge domain, THE System SHALL validate that all terms have definitions and save the domain
4. WHEN a student attempts to create a domain with duplicate terms, THE System SHALL prevent creation and notify the student
5. WHEN a student views their created domains, THE System SHALL display a list of all domains they have authored

### Requirement 3: Quiz Interface and Guided Learning

**User Story:** As a student, I want to take interactive quizzes on knowledge domains, so that I can learn and test my understanding of terminology.

#### Acceptance Criteria

1. WHEN a student selects a knowledge domain for learning, THE System SHALL initiate a guided quiz session
2. WHEN presenting a quiz question, THE System SHALL display a term and provide input for the student's definition
3. WHEN a student submits an answer, THE System SHALL evaluate the response and provide immediate feedback
4. WHEN a student completes all terms in a domain, THE System SHALL display a completion summary with performance metrics
5. WHEN a student wants to exit a quiz early, THE System SHALL save their current progress and allow resumption later
6. WHEN a student resumes an incomplete quiz, THE System SHALL continue from where they left off

### Requirement 4: Progress Tracking

**User Story:** As a student, I want to see my learning progress, so that I can understand my mastery level and identify areas needing improvement.

#### Acceptance Criteria

1. WHEN a student completes quiz questions, THE System SHALL record their performance for each term
2. WHEN a student views their progress dashboard, THE System SHALL display completion percentages for each knowledge domain
3. WHEN a student reviews domain-specific progress, THE System SHALL show which terms they have mastered and which need more practice
4. WHEN a student retakes quiz questions, THE System SHALL update their progress metrics accordingly
5. WHEN calculating mastery, THE System SHALL consider both accuracy and consistency across multiple attempts

### Requirement 5: Data Persistence and Session Management

**User Story:** As a student, I want my progress and content to be saved automatically, so that I can continue learning across different sessions and devices.

#### Acceptance Criteria

1. WHEN a student creates or modifies content, THE System SHALL persist changes to the database immediately
2. WHEN a student's session expires, THE System SHALL maintain their progress data and allow seamless continuation
3. WHEN a student accesses the system from different devices, THE System SHALL synchronize their progress and content
4. WHEN the system experiences interruptions, THE System SHALL recover user data without loss
5. WHEN a student deletes a knowledge domain, THE System SHALL remove all associated data while preserving progress history

### Requirement 6: Domain-Agnostic Architecture

**User Story:** As a system architect, I want the system to handle any knowledge domain without code changes, so that the platform can scale to support diverse learning subjects.

#### Acceptance Criteria

1. WHEN new knowledge domains are added, THE System SHALL process them using the same core logic regardless of subject matter
2. WHEN storing domain data, THE System SHALL separate content payload from structural management
3. WHEN traversing knowledge domains, THE System SHALL use generic tree operations independent of content type
4. WHEN retrieving domain information, THE System SHALL handle any subject area through consistent interfaces
5. WHEN extending functionality, THE System SHALL maintain separation between domain logic and content interpretation

### Requirement 7: Answer Evaluation System

**User Story:** As a student, I want my quiz answers to be evaluated intelligently, so that I receive fair and accurate feedback on my understanding.

#### Acceptance Criteria

1. WHEN a student submits an answer, THE System SHALL compare it against the correct definition using a custom developed language model
2. WHEN evaluating answers, THE System SHALL account for synonyms, alternative phrasings, and partial correctness
3. WHEN an answer is partially correct, THE System SHALL provide constructive feedback highlighting correct and incorrect elements
4. WHEN an answer is completely incorrect, THE System SHALL display the correct definition and explanation

### Requirement 8: Subject Selection

**User Story:** As a system administrator, I want to be able to feed new subjects into the System by a batch propcess.

#### Acceptance Criteria

1. WHEN a system administrator accesses the administrator page, they should see the batch upload option 
2. WHEN a system administrator wants to do a batch upload, the System SHALL provide a search facility to search for and select a file
3. WHEN a system administrator selects a file, THE System SHALL confirm that it adheres to the JSON format present in the file named python_built_in_decorators_improved.json in the same directory as this file
4. WHEN a system administrator clicks upload, the System will insert the new subjest and the relevant data in the System database.