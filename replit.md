# Nano Banana API

## Overview

This project is a Flask-based API wrapper for the NanoBanana AI image generation service. It provides a simplified interface to interact with the NanoBanana API, handling task submission and polling for results. The service includes user session tracking to maintain image context across requests.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Backend Framework
- **Framework**: Flask (Python)
- **Rationale**: Lightweight and simple for building REST APIs
- **Production Server**: Gunicorn for handling concurrent requests

### API Design
- **Pattern**: REST API with GET endpoints
- **Main Endpoint**: `/nanobanana` - accepts prompt, image URL, and user ID parameters
- **External API Integration**: Wraps the NanoBanana AI API (`api.nanobananaapi.ai`)

### State Management
- **Approach**: In-memory dictionary (`user_history`)
- **Purpose**: Tracks the last image URL per user ID to maintain context between requests
- **Limitation**: State is lost on server restart (not persistent)

### Task Processing
- **Pattern**: Polling-based async handling
- **Flow**: Submit task → Poll for completion → Return result
- **Polling Config**: Max 30 attempts with 2-second intervals (up to 60 seconds total)

### Authentication
- **External API Auth**: Bearer token authentication using API key from environment variables
- **Fallback**: Hardcoded default API key (should be moved to environment variable only)

## External Dependencies

### Third-Party APIs
- **NanoBanana API** (`https://api.nanobananaapi.ai/api/v1/nanobanana`)
  - Used for AI image generation/processing
  - Requires API key via `API_KEYS_1` environment variable
  - Endpoints used: `/record-info` for task status polling

### Python Packages
- **Flask**: Web framework
- **Requests**: HTTP client for external API calls
- **Gunicorn**: WSGI HTTP server for production deployment

### Environment Variables
- `API_KEYS_1`: NanoBanana API authentication key (required for production)