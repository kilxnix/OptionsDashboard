from flask import Flask, jsonify
from run_autonomous_scan import run_autonomous_scan

app = Flask(__name__)


@app.route("/")
def index():
    return jsonify({
        "status": "online",
        "message": "Autonomous scanner is running."
    })


@app.route("/scan", methods=["GET"])
def trigger_scan():
    result = run_autonomous_scan(dry_run=False)

    if not result or not result.get("results"):
        return jsonify({
            "status": "no-results",
            "message": "Scanner ran but found no valid trade plans.",
            "digest": result["digest"] if result else "No output"
        }), 200

    return jsonify({
        "status":
        "completed",
        "digest":
        result["digest"],
        "top_result":
        result.get("summary", {}).get("top_symbol", "N/A")
    }), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
