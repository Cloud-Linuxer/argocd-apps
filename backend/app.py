from flask import Flask, jsonify
import os

app = Flask(__name__)

@app.route('/health')
def health():
    return jsonify({"status": "healthy", "service": "backend"})

@app.route('/api/info')
def info():
    return jsonify({
        "service": "backend-api",
        "version": "2.0.4",
        "environment": os.getenv("ENV", "development")
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
