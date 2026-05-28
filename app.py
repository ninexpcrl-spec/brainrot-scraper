from flask import Flask, request, Response, jsonify, render_template_string
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import requests
import json
import os
import time
import logging
from datetime import datetime

app = Flask(__name__)

# ========================= CONFIGURAÇÕES =========================
API_SECRET = "BrainrotScanner2026!xK9#mP$7vQ2@nL8"
PLACE_ID = "109983668079237"
BLOCKED_PLACE_ID = "96342491571673"
ALLOWED_IPS = ["143.0.229.43", "127.0.0.1", "::1"]

limiter = Limiter(get_remote_address, app=app, default_limits=["40 per minute"], storage_uri="memory://")

job_queue = []
detections = []
recent_jobs = {}

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')

# ========================= DASHBOARD HTML BONITO =========================
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="pt">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🧠 Brainrot Scraper Dashboard</title>
    <style>
        body { font-family: 'Segoe UI', sans-serif; background: #0f0f1a; color: #00ff9d; margin: 0; padding: 20px; }
        .container { max-width: 1100px; margin: auto; }
        h1 { color: #00ff9d; text-align: center; }
        .card { background: #1a1a2e; border-radius: 12px; padding: 20px; margin: 15px 0; box-shadow: 0 4px 15px rgba(0,255,157,0.1); }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #333; }
        th { background: #16213e; }
        .status { padding: 5px 12px; border-radius: 20px; font-size: 14px; }
        .running { background: #00ff9d; color: black; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🧠 Brainrot Scraper Dashboard</h1>
        <div class="card">
            <h2>📊 Status Geral</h2>
            <p><strong>Status:</strong> <span class="status running">✅ ONLINE</span></p>
            <p><strong>Jobs na Fila:</strong> {{ queue_size }}</p>
            <p><strong>Detecções Salvas:</strong> {{ detections_count }}</p>
            <p><strong>Place ID:</strong> {{ place_id }}</p>
        </div>
        
        <div class="card">
            <h2>📋 Últimas Detecções</h2>
            {% if detections %}
                <table>
                    <tr><th>Hora</th><th>Job ID</th><th>Top Pet</th></tr>
                    {% for d in detections[-10:] %}
                    <tr>
                        <td>{{ d.received_at[-8:] }}</td>
                        <td>{{ d.jobId[:15] }}...</td>
                        <td>{{ d.topPet.name if d.topPet else 'N/A' }}</td>
                    </tr>
                    {% endfor %}
                </table>
            {% else %}
                <p>Nenhuma detecção ainda.</p>
            {% endif %}
        </div>
    </div>
</body>
</html>
"""

# ========================= FUNÇÕES =========================
def is_allowed_ip():
    ip = request.remote_addr
    return ip in ALLOWED_IPS or ip.startswith("192.168.") or ip.startswith("10.")

def check_secret():
    secret = request.headers.get("X-API-Secret")
    return secret == API_SECRET

def fetch_jobs():
    # (mesma função de antes - mantida igual)
    url = f"https://games.roblox.com/v1/games/{PLACE_ID}/servers/Public"
    try:
        response = requests.get(url, params={"sortOrder": "Asc", "limit": 100}, timeout=15)
        response.raise_for_status()
        data = response.json()
        jobs = []
        now = time.time()
        if "data" in data:
            for server in data["data"]:
                job_id = server.get("id")
                place_id = str(server.get("placeId", PLACE_ID))
                if place_id == BLOCKED_PLACE_ID: continue
                if job_id in recent_jobs and now - recent_jobs[job_id] < 7200: continue
                if job_id:
                    jobs.append({"jobId": job_id, "placeId": place_id, "players": server.get("playing", 0)})
        return jobs
    except:
        return []

# ========================= ROTAS =========================
@app.route('/')
def dashboard():
    return render_template_string(DASHBOARD_HTML, 
                                queue_size=len(job_queue),
                                detections_count=len(detections),
                                place_id=PLACE_ID,
                                detections=detections)

@app.route('/health')
def health_check():
    return jsonify({"status": "running", "queue_size": len(job_queue), "detections_count": len(detections), "place_id": PLACE_ID})

@app.route('/get-job', methods=['GET', 'OPTIONS'])
def get_job():
    if request.method == 'OPTIONS': return Response("", 200)
    if not is_allowed_ip() or not check_secret():
        return jsonify({"error": "Access denied"}), 403

    global job_queue
    if len(job_queue) < 10:
        new_jobs = fetch_jobs()
        if new_jobs:
            job_queue.extend(new_jobs)

    if job_queue:
        job = job_queue.pop(0)
        recent_jobs[job['jobId']] = time.time()
        return jsonify({"jobId": job['jobId'], "placeId": job['placeId'], "players": job['players']})
    
    return jsonify({"error": "No jobs available"}), 404

@app.route('/detection', methods=['POST'])
def receive_detection():
    if not is_allowed_ip() or not check_secret():
        return jsonify({"error": "Access denied"}), 403
    try:
        data = request.get_json()
        if data:
            detections.append({**data, "received_at": datetime.utcnow().isoformat()})
            if len(detections) > 50:
                detections[:] = detections[-50:]
        return jsonify({"status": "received"}), 200
    except:
        return jsonify({"error": "Invalid data"}), 400

if __name__ == '__main__':
    print("🧠 Brainrot Scraper + Dashboard Iniciado!")
    job_queue = fetch_jobs()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
