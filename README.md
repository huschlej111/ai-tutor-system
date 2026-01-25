# Know-It-All Tutor System

A serverless web application that transforms terminology-heavy subjects into interactive, hands-on learning experiences. Built with AWS Lambda, React, and a custom ML model for intelligent answer evaluation.

## 🎯 Project Vision

To empower students of any subject by providing an interactive, web-based learning environment that transforms complex vocabularies into intuitive, progressive learning experiences.

**Target Users**: Professionals preparing for AWS certification, Python developers, and anyone mastering terminology-heavy subjects.

## 🏗️ Architecture Overview

- **Frontend**: React 18 + TypeScript + Tailwind CSS
- **Backend**: AWS Lambda (Node.js/Python) + Aurora Serverless PostgreSQL
- **ML Model**: Custom fine-tuned sentence transformer for semantic answer evaluation
- **Infrastructure**: Serverless-first with AWS Always Free tier optimization

## 📁 Project Structure

```
├── artifacts/                          # Professional UI design artifacts (HTML)
│   ├── sitemap.html                    # Interactive information architecture
│   ├── user_flow_onboarding.html       # Complete user journey mapping
│   ├── wireframe_dashboard.html        # Responsive dashboard layouts
│   ├── wireframe_quiz_interface.html   # Interactive learning interface
│   └── component_library.html          # Complete design system
├── final_similarity_model/             # Custom ML model for answer evaluation
├── .kiro/specs/tutor-system/          # Complete system specifications
│   ├── requirements.md                 # Functional requirements
│   ├── design.md                      # System architecture & UI design
│   ├── datamodel.md                   # Database design & queries
│   ├── model_interface.md             # ML model integration
│   ├── vision.md                      # Product vision & roadmap
│   ├── qa_testing_plan.md             # Testing strategy
│   ├── ci-cd_plan.md                  # Deployment automation
│   └── ui/                            # UI/UX design documentation
│       ├── ui_design.md               # Design plan & principles
│       ├── design_system.md           # Component library specs
│       ├── wireframes.md              # Low-fidelity layouts
│       ├── user_flows.md              # User journey diagrams
│       ├── sitemap.md                 # Information architecture
│       ├── mood_boards_style_tiles.md # Visual design direction
│       └── technical_specifications.md # Implementation details
└── README.md                          # This file
```

## 🚀 Key Features

### For Students
- **Interactive Quizzes**: Semantic answer evaluation with immediate feedback
- **Progress Tracking**: Visual progress indicators and achievement system
- **Domain-Agnostic**: Works with any terminology-heavy subject
- **Responsive Design**: Optimized for desktop, tablet, and mobile

### For Content Creators
- **Easy Domain Creation**: Intuitive interface for adding knowledge domains
- **Bulk Import**: JSON-based batch upload for large content sets
- **Preview & Validation**: Test content before publishing

### For Administrators
- **Batch Upload**: Efficient content management for large datasets
- **Analytics Dashboard**: Usage metrics and performance insights
- **Content Moderation**: Review and approve user-generated content

## 🎨 Design System

The system features a comprehensive design system with:
- **Professional aesthetic** suitable for certification prep and professional development
- **Accessibility-first** approach with WCAG 2.1 AA compliance
- **Responsive design** with mobile-first approach
- **Interactive components** with smooth animations and feedback

**View Design Artifacts**: Open any HTML file in the `artifacts/` directory to see interactive design documentation.

## 🧠 ML-Powered Answer Evaluation

- **Custom Model**: Fine-tuned DistilBERT sentence transformer
- **Semantic Understanding**: Recognizes synonyms and alternative phrasings
- **Graduated Feedback**: Constructive guidance based on similarity scores
- **Domain-Agnostic**: Works across any knowledge domain without retraining

## 📊 Technical Highlights

### Performance Targets
- **First Contentful Paint**: < 1.5 seconds
- **Time to Interactive**: < 3 seconds
- **Lighthouse Score**: > 90 across all metrics
- **Bundle Size**: < 250KB gzipped

### Scalability
- **Serverless Architecture**: Auto-scaling with AWS Lambda
- **Database**: Aurora Serverless PostgreSQL with connection pooling
- **CDN**: CloudFront distribution for global performance
- **Cost-Optimized**: Designed for AWS Always Free tier

## 🔧 Development

### Prerequisites
- Node.js 18+
- Python 3.11+
- AWS CLI configured
- Docker and Docker Compose (for LocalStack)

### Local Development with LocalStack

This project uses [LocalStack](https://localstack.cloud/) for local AWS development and testing. LocalStack provides a fully functional local AWS cloud stack that runs in Docker.

#### Quick Start with LocalStack
```bash
# Clone repository
git clone <repository-url>
cd know-it-all-tutor

# Install dependencies
make install

# First time setup (creates database + starts LocalStack)
make local-dev

# Daily usage (just start LocalStack)
make localstack-start

# Run tests against LocalStack
make local-test

# Stop LocalStack when done (PostgreSQL keeps running)
make localstack-stop
```

#### Database Options

**Option 1: Use Existing PostgreSQL (Recommended)**
If you have PostgreSQL installed on your system (which you do), the setup will use your existing PostgreSQL service:
```bash
# Setup uses your existing PostgreSQL on port 5432
make local-dev
```

**Option 2: Use Containerized PostgreSQL**
If you prefer to use a separate PostgreSQL container on port 5433:
```bash
# Use alternative compose file
docker-compose -f docker-compose.localstack-with-db.yml up -d
make localstack-setup
```

#### LocalStack Development Environment

The project uses LocalStack RDS emulation for Aurora Serverless-like development:

```bash
make local-dev
```

#### LocalStack Services Available
- **Lambda**: Serverless functions
- **RDS**: PostgreSQL emulation (Aurora Serverless-like)
- **S3**: Object storage
- **API Gateway**: REST APIs
- **Secrets Manager**: Credential storage
- **Authentication**: Mock authentication (Cognito requires paid LocalStack tier)
- **CloudWatch**: Logging and monitoring
- **IAM**: Identity and access management

#### LocalStack Commands
```bash
# Development Environment
make local-dev          # Start RDS emulation environment

# Testing & Validation
make localstack-verify  # Verify all services
make test-rds          # Test RDS connectivity
make test-rds-secret   # Test Secrets Manager integration

# Management
make localstack-status # Check status
make localstack-logs   # View logs
make localstack-stop   # Stop services
make localstack-stop

# Full local development setup (start + setup)
make local-dev
```

#### Environment Configuration
LocalStack uses `.env.localstack` for configuration:
- **LocalStack endpoint**: `http://localhost:4566`
- **PostgreSQL**: `localhost:5432`
- **Test credentials**: `test/test` (AWS keys)
- **Sample data**: Pre-loaded users and domains

#### LocalStack Web UI
Access the LocalStack Web UI at: `http://localhost:4566/_localstack/health`

### Traditional Development
```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Run tests
npm test
```

### Documentation
- **System Design**: See `.kiro/specs/tutor-system/design.md`
- **API Documentation**: See `.kiro/specs/tutor-system/model_interface.md`
- **UI Components**: Open `artifacts/component_library.html`
- **User Flows**: Open `artifacts/user_flow_onboarding.html`

## 🧪 Testing Strategy

- **Unit Tests**: Jest + React Testing Library
- **Integration Tests**: API and database integration
- **E2E Tests**: Playwright for complete user journeys
- **Property-Based Tests**: fast-check for comprehensive coverage
- **Accessibility Tests**: jest-axe for WCAG compliance
- **Performance Tests**: Lighthouse CI for web vitals

## 🚀 Deployment

The system uses AWS CodePipeline for automated deployment:
- **Development**: Auto-deploy from `develop` branch
- **Production**: Auto-deploy from `main` branch
- **Infrastructure**: AWS CDK for infrastructure as code
- **Database**: Automated migrations with rollback support

## 📈 Success Metrics

- **Retention**: Percentage of users completing full domains
- **Activation**: Time from landing to first quiz completion
- **Engagement**: Average session duration and return visits
- **Learning Effectiveness**: Improvement in quiz scores over time

## 🤝 Contributing

1. Review the system design in `.kiro/specs/tutor-system/`
2. Check the UI design system in `artifacts/component_library.html`
3. Follow the testing strategy outlined in `qa_testing_plan.md`
4. Ensure accessibility compliance with design standards

## 📄 License

[License information to be added]

---

**Built with ❤️ for effective learning and professional development**