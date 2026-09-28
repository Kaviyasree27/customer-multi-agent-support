from flask import Flask, jsonify
from flask_cors import CORS

from config import Config
from extensions import jwt, init_indexes
from models import user_model
from utils.helpers import error_response


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # CORS configuration
    CORS(
        app,
        resources={r"/api/*": {"origins": Config.CORS_ORIGIN}},
        supports_credentials=True
    )

    # Initialize JWT
    jwt.init_app(app)

    # Initialize MongoDB indexes
    init_indexes()

    # Bootstrap default admin account
    user_model.ensure_admin(
        Config.ADMIN_EMAIL,
        Config.ADMIN_PASSWORD
    )

    # Register API blueprints
    from routes.auth import bp as auth_bp
    from routes.profile import bp as profile_bp
    from routes.chat import bp as chat_bp
    from routes.orders import bp as orders_bp
    from routes.tickets import bp as tickets_bp, feedback_bp
    from routes.admin import bp as admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(orders_bp)
    app.register_blueprint(tickets_bp)
    app.register_blueprint(feedback_bp)
    app.register_blueprint(admin_bp)

    # Homepage
    @app.get("/")
    def home():
        return jsonify({
            "message": "AI Multi-Agent Customer Support System",
            "status": "running",
            "backend": "Flask",
            "database": "MongoDB",
            "llm_provider": "Groq",
            "endpoints": {
                "health": "/api/health"
            }
        }), 200

    # API health check
    @app.get("/api/health")
    def health():
        return jsonify({
            "status": "ok",
            "message": "Backend is running successfully"
        }), 200

    # Error handlers
    @app.errorhandler(404)
    def not_found(e):
        return error_response("Not found.", 404)

    @app.errorhandler(500)
    def server_error(e):
        return error_response(
            "Internal server error. Please try again.",
            500
        )

    # JWT error handlers
    @jwt.unauthorized_loader
    def unauthorized(reason):
        return error_response(
            f"Authentication required: {reason}",
            401
        )

    @jwt.invalid_token_loader
    def invalid_token(reason):
        return error_response(
            f"Invalid token: {reason}",
            422
        )

    @jwt.expired_token_loader
    def expired_token(header, payload):
        return error_response(
            "Session expired, please log in again.",
            401
        )

    return app


app = create_app()


if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True,
        use_reloader=False
    )