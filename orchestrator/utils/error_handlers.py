"""
Global error handlers for the application
Prevents information disclosure through error messages
"""
import logging
from flask import jsonify, request, g
from werkzeug.exceptions import HTTPException
from sqlalchemy.exc import SQLAlchemyError
import uuid
import time

logger = logging.getLogger(__name__)

def register_error_handlers(app):
    """Register all error handlers with the Flask app"""
    
    @app.before_request
    def before_request():
        """Add correlation ID and timing to each request"""
        g.correlation_id = str(uuid.uuid4())
        g.request_start = time.time()
    
    @app.after_request
    def after_request(response):
        """Log request completion"""
        if hasattr(g, 'request_start'):
            duration = time.time() - g.request_start
            logger.info(
                f"Request completed: {request.method} {request.path} - "
                f"{response.status_code} - {duration:.3f}s - {g.correlation_id}"
            )
        
        # Add correlation ID to response headers
        if hasattr(g, 'correlation_id'):
            response.headers['X-Correlation-ID'] = g.correlation_id
        
        return response
    
    @app.errorhandler(404)
    def not_found(e):
        """Handle 404 errors"""
        logger.warning(f"404 Not Found: {request.path} - {g.correlation_id}")
        return jsonify({
            'error': {
                'message': 'Resource not found',
                'code': 404,
                'correlation_id': g.correlation_id
            }
        }), 404
    
    @app.errorhandler(400)
    def bad_request(e):
        """Handle 400 errors"""
        logger.warning(f"400 Bad Request: {request.path} - {str(e)} - {g.correlation_id}")
        return jsonify({
            'error': {
                'message': 'Invalid request',
                'code': 400,
                'correlation_id': g.correlation_id
            }
        }), 400
    
    @app.errorhandler(401)
    def unauthorized(e):
        """Handle 401 errors"""
        logger.warning(f"401 Unauthorized: {request.path} - {g.correlation_id}")
        return jsonify({
            'error': {
                'message': 'Authentication required',
                'code': 401,
                'correlation_id': g.correlation_id
            }
        }), 401
    
    @app.errorhandler(403)
    def forbidden(e):
        """Handle 403 errors"""
        logger.warning(f"403 Forbidden: {request.path} - {g.correlation_id}")
        return jsonify({
            'error': {
                'message': 'Access denied',
                'code': 403,
                'correlation_id': g.correlation_id
            }
        }), 403
    
    @app.errorhandler(405)
    def method_not_allowed(e):
        """Handle 405 errors"""
        logger.warning(f"405 Method Not Allowed: {request.method} {request.path} - {g.correlation_id}")
        return jsonify({
            'error': {
                'message': 'Method not allowed',
                'code': 405,
                'correlation_id': g.correlation_id
            }
        }), 405
    
    @app.errorhandler(413)
    def request_entity_too_large(e):
        """Handle 413 errors"""
        logger.warning(f"413 Request Entity Too Large: {request.path} - {g.correlation_id}")
        return jsonify({
            'error': {
                'message': 'Request too large',
                'code': 413,
                'correlation_id': g.correlation_id
            }
        }), 413
    
    @app.errorhandler(429)
    def too_many_requests(e):
        """Handle 429 errors (rate limiting)"""
        logger.warning(f"429 Too Many Requests: {request.path} - {g.correlation_id}")
        return jsonify({
            'error': {
                'message': 'Too many requests. Please try again later.',
                'code': 429,
                'correlation_id': g.correlation_id
            }
        }), 429
    
    @app.errorhandler(HTTPException)
    def handle_http_exception(e):
        """Handle all other HTTP exceptions"""
        logger.error(f"HTTP Exception {e.code}: {request.path} - {str(e)} - {g.correlation_id}")
        return jsonify({
            'error': {
                'message': e.description or 'An error occurred',
                'code': e.code,
                'correlation_id': g.correlation_id
            }
        }), e.code
    
    @app.errorhandler(SQLAlchemyError)
    def handle_database_error(e):
        """Handle database errors"""
        logger.error(
            f"Database error: {request.path} - {type(e).__name__} - {g.correlation_id}",
            exc_info=True
        )
        return jsonify({
            'error': {
                'message': 'Database operation failed',
                'code': 500,
                'correlation_id': g.correlation_id
            }
        }), 500
    
    @app.errorhandler(Exception)
    def handle_exception(e):
        """Handle all other exceptions"""
        logger.error(
            f"Unhandled exception: {request.path} - {type(e).__name__}: {str(e)} - {g.correlation_id}",
            exc_info=True
        )
        
        # In production, never expose the actual error
        if app.config.get('DEBUG', False):
            message = f"Internal error: {str(e)}"
        else:
            message = 'Internal server error'
        
        return jsonify({
            'error': {
                'message': message,
                'code': 500,
                'correlation_id': g.correlation_id
            }
        }), 500

def log_security_event(event_type, details=None, user_id=None):
    """Log security-relevant events"""
    logger.warning(
        f"SECURITY EVENT - {event_type} - User: {user_id} - "
        f"IP: {request.remote_addr} - Details: {details} - "
        f"Correlation ID: {getattr(g, 'correlation_id', 'N/A')}"
    )