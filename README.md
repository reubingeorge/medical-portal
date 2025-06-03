# Medical Portal

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/Python-3.10-3776AB?style=flat&logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-4.2-092E20?style=flat&logo=django&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-316192?style=flat&logo=postgresql&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-7.0-DC382D?style=flat&logo=redis&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-24.0-2496ED?style=flat&logo=docker&logoColor=white)
![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4-412991?style=flat&logo=openai&logoColor=white)
![HTMX](https://img.shields.io/badge/HTMX-1.9-3366CC?style=flat&logo=htmx&logoColor=white)

A comprehensive medical portal for patients, doctors, and administrators with advanced document management, chat support using RAG (Retrieval-Augmented Generation), and integrated AI analysis.

## Features

- **User Role Management**: Patient, Doctor, Admin roles with tailored dashboards
- **Medical Document Management**: Upload, view, search, and manage medical records
- **Advanced RAG Chat System**: AI-powered medical information assistant
- **Multi-language Support**: Automatic translation and language detection
- **Secure Authentication**: Role-based access control and secure login flows
- **Audit Logging**: Comprehensive activity tracking for security and compliance
- **OCR Document Processing**: Automated text extraction from medical documents
- **Cancer Type Matching**: Intelligent cancer type classification system
- **Responsive Design**: Modern interface that works on all devices

## Getting Started

### Prerequisites

- Docker and Docker Compose
- Git

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/medical-portal.git
   cd medical-portal
   docker compose up --build
   ```

2. Start the Docker containers:
   ```bash
   docker-compose up -d
   ```

3. Access the application:
   - Web application: http://localhost:8080
   - PostgreSQL database: localhost:5432 (via pgAdmin or other DB client)
   - Redis: localhost:6379

### Default Admin Credentials

```
Email: admin@example.com
Password: adminpass
```

## Architecture

The Medical Portal uses a modern architecture with these components:

- **Backend**: Django REST Framework
- **Database**: PostgreSQL with pgvector extension for vector embeddings
- **Cache**: Redis for session management and caching
- **AI Integration**: OpenAI API for RAG and document analysis
- **OCR**: PaddleOCR for document text extraction
- **Document Storage**: File system with secure access controls
- **Authentication**: Custom user model with role-based permissions

## Core Components

### 1. User Management

- Custom user model with role-based access
- Email verification workflow
- Password reset functionality
- Secure authentication with brute force protection

### 2. Medical Records

- Patient record management
- Medical document upload and processing
- Document OCR and text extraction
- Cancer type classification
- Audit trail for all document actions

### 3. Advanced RAG System

- Hybrid search with reranking
- Intelligent caching for similar queries
- Advanced document processing with smart chunking
- Performance monitoring and analytics
- Confidence scoring for response quality

### 4. Security Features

- CSRF protection across all forms
- Content Security Policy implementation
- Secure HTTP headers
- Input sanitization
- Audit logging for security events
- Rate limiting for sensitive operations

## Technical Stack

### Core Technologies
- **Backend**: Python 3.10, Django 4.2, Django REST Framework
- **Frontend**: HTML5, CSS3, JavaScript (ES6), HTMX
- **Database**: PostgreSQL 15 with pgvector extension
- **Caching**: Redis 7.0
- **AI/ML**: OpenAI GPT-4, LangChain, Transformers, PaddleOCR
- **Infrastructure**: Docker, Docker Compose, Nginx
- **Testing**: Pytest, Coverage.py

### Key Features
- JWT Authentication with OAuth2 support
- Real-time WebSocket connections
- HIPAA-compliant security measures
- REST API with Swagger documentation
- Automated CI/CD with GitHub Actions

## Development

### Project Structure

```
medical-portal/
├── backend/              # Django backend
│   ├── apps/             # Django applications
│   │   ├── accounts/     # User management
│   │   ├── audit/        # Audit logging
│   │   ├── chat/         # RAG chat system
│   │   └── medical/      # Medical record management
│   ├── config/           # Django settings
│   ├── media/            # Uploaded files
│   ├── staticfiles/      # Collected static files
│   ├── templates/        # Backend templates
│   └── utils/            # Utility functions
├── docker/               # Docker configuration
│   ├── Dockerfile        # Main Dockerfile
│   ├── entrypoint.sh     # Container entrypoint
│   ├── dev.env           # Development environment variables
│   └── prod.env          # Production environment variables
├── frontend/             # Frontend assets
│   ├── static/           # Static assets
│   │   ├── css/          # CSS styles
│   │   ├── img/          # Images
│   │   └── js/           # JavaScript files
│   └── templates/        # Frontend templates
├── docker-compose.yml    # Docker Compose configuration
└── requirements.txt      # Python dependencies
```

### Environment Variables

Key environment variables in `docker/dev.env` and `docker/prod.env`:

- `DJANGO_ENV`: Environment (development/production)
- `DJANGO_SECRET_KEY`: Secret key for Django
- `DJANGO_DEBUG`: Debug mode
- `OPENAI_API_KEY`: OpenAI API key
- `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`: Database credentials
- `EMAIL_*`: Email configuration

### Adding a New Feature

1. Create new models in the appropriate app
2. Create migrations with `python manage.py makemigrations`
3. Create views and templates
4. Add URL routes
5. Update permissions and access controls
6. Add tests for new functionality

## Key Components

### Advanced RAG System

The portal features a state-of-the-art Retrieval-Augmented Generation system:

- **Hybrid Search**: Combines semantic and keyword-based search
- **Cross-Encoder Reranking**: Improved relevance scoring
- **Intelligent Caching**: Similar query detection and prioritization
- **Smart Chunking**: Context-aware document splitting
- **Confidence Scoring**: Quality assessment of responses

### Security Measures

- **CSRF Protection**: Prevents cross-site request forgery
- **Secure Forms**: All forms use POST method with proper validation
- **Security Headers**: Comprehensive HTTP security headers
- **Input Sanitization**: Protection against XSS and injection
- **Rate Limiting**: Prevents brute force attacks
- **Audit Logging**: Comprehensive tracking of security-related events

## Performance Optimization

- **Document Chunking**: Optimized for retrieval performance
- **Vector Embeddings**: Efficient similarity search
- **Caching**: Redis-based caching for frequent queries
- **Asynchronous Processing**: Background tasks for document processing
- **Query Optimization**: Efficient database queries with proper indexing

## Testing

Run tests with Docker:

```bash
docker-compose exec web python backend/manage.py test
```

Or use pytest:

```bash
docker-compose exec web pytest backend/
```

## Security

- Update default credentials in production
- Secure the OpenAI API key
- Use HTTPS in production
- Follow the principle of least privilege for user roles
- Regular security audits and updates

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

- [Django](https://www.djangoproject.com/)
- [PostgreSQL](https://www.postgresql.org/)
- [pgvector](https://github.com/pgvector/pgvector)
- [OpenAI](https://openai.com/)
- [LangChain](https://www.langchain.com/)
- [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR)
- [HTMX](https://htmx.org/)