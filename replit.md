# Image Format Converter

## Overview

This is a Flask-based web application that provides image format conversion capabilities. The application allows users to upload images in various formats (PNG, JPG/JPEG, WebP, AVIF) and convert them to different output formats. It features a modern, responsive web interface with drag-and-drop functionality for easy file uploads.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture
- **Single Page Application**: Uses a single HTML template (`index.html`) with embedded CSS and JavaScript
- **Responsive Design**: Modern CSS with flexbox layout and gradient backgrounds
- **Interactive UI**: Features drag-and-drop file upload area with visual feedback
- **Client-side Validation**: File type and size validation before upload

### Backend Architecture
- **Framework**: Flask web framework for Python
- **Image Processing**: PIL (Python Imaging Library) with pillow-avif plugin for extended format support
- **File Handling**: Werkzeug utilities for secure filename handling
- **API Design**: RESTful endpoint structure with JSON responses
- **Error Handling**: Comprehensive error handling with appropriate HTTP status codes

### Data Processing
- **In-Memory Processing**: Images are processed in memory using BytesIO streams
- **Format Support**: Supports PNG, JPG/JPEG, WebP, and AVIF formats for both input and output
- **File Size Limits**: 16MB maximum file size limit to prevent resource exhaustion
- **Security**: File type validation using both extension and MIME type checking

### Configuration
- **Production Environment**: Application configured for production deployment
- **Upload Restrictions**: Strict file type and size limitations for security
- **MIME Type Validation**: Dual validation using file extensions and content types

## External Dependencies

### Python Packages
- **Flask**: Web framework for handling HTTP requests and responses
- **Pillow (PIL)**: Core image processing library
- **pillow-avif**: Plugin to add AVIF format support to Pillow
- **Werkzeug**: WSGI utilities (included with Flask)

### Frontend Dependencies
- **No External Libraries**: Uses vanilla HTML, CSS, and JavaScript without external frameworks
- **System Fonts**: Relies on system font stack for consistent typography

### Runtime Requirements
- **Python Environment**: Requires Python 3.x runtime
- **Memory**: In-memory image processing requires sufficient RAM for large images
- **File System**: Temporary file handling capabilities