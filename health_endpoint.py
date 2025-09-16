# ADD THIS TO YOUR main.py FILE

@app.route("/api/health", methods=["GET"])
def health_check():
    """Health check endpoint for Docker"""
    try:
        from sqlalchemy import text
        db.session.execute(text('SELECT 1'))
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
    
    return jsonify({
        "status": "healthy" if db_status == "healthy" else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "optionsscanner-api",
        "database": db_status
    }), 200 if db_status == "healthy" else 503

@app.route("/health", methods=["GET"])
def simple_health():
    """Simple health check"""
    return "OK", 200
