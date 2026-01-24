"""
Web Dashboard for LLM Attack Lab

Provides a visual interface for exploring and simulating LLM attacks.
Includes OpenTelemetry integration for observability.
"""

import os
import json
import time
from flask import Flask, render_template, request, jsonify
from llm_attack_lab.core.llm_simulator import LLMSimulator, SecurityLevel
from llm_attack_lab.attacks import ATTACK_REGISTRY
from llm_attack_lab.monitoring.metrics import get_metrics_collector
from llm_attack_lab.monitoring.logger import get_logger

# OpenTelemetry integration
try:
    from llm_attack_lab.monitoring.otel import init_telemetry, get_otel_manager
    OTEL_ENABLED = True
except ImportError:
    OTEL_ENABLED = False
    init_telemetry = None
    get_otel_manager = None

# Flask instrumentation
try:
    from opentelemetry.instrumentation.flask import FlaskInstrumentor
    FLASK_INSTRUMENTATION = True
except ImportError:
    FLASK_INSTRUMENTATION = False

app = Flask(__name__, template_folder='templates', static_folder='static')

# Initialize OpenTelemetry if available
otel_manager = None
if OTEL_ENABLED:
    try:
        otel_manager = init_telemetry()
        if FLASK_INSTRUMENTATION:
            FlaskInstrumentor().instrument_app(app)
    except Exception as e:
        print(f"Warning: Could not initialize OpenTelemetry: {e}")

# Global instances
simulator = LLMSimulator()
metrics = get_metrics_collector()
logger = get_logger("web")


@app.route('/')
def index():
    """Main dashboard page - redirects to dashboard"""
    return render_template('dashboard.html')


@app.route('/classic')
def classic():
    """Classic/legacy interface"""
    return render_template('index.html')


@app.route('/dashboard')
def dashboard():
    """Advanced security dashboard"""
    return render_template('dashboard.html')


@app.route('/api/status')
def get_status():
    """Get current simulator status"""
    status = simulator.get_status()

    # Update OTel gauges
    if otel_manager:
        otel_manager.set_security_level(SecurityLevel[status['security_level']].value)
        otel_manager.set_compromised_status(status['is_compromised'])

    return jsonify(status)


@app.route('/api/attacks')
def get_attacks():
    """Get list of available attacks"""
    attacks = []
    for key, attack_class in ATTACK_REGISTRY.items():
        attack = attack_class()
        attacks.append({
            'id': key,
            'name': attack.name,
            'description': attack.description,
            'category': attack.category,
            'severity': attack.severity,
        })
    return jsonify(attacks)


@app.route('/api/attack/<attack_id>')
def get_attack_details(attack_id):
    """Get details for a specific attack"""
    if attack_id not in ATTACK_REGISTRY:
        return jsonify({'error': 'Attack not found'}), 404

    attack_class = ATTACK_REGISTRY[attack_id]
    attack = attack_class()

    return jsonify({
        'id': attack_id,
        'name': attack.name,
        'description': attack.description,
        'category': attack.category,
        'severity': attack.severity,
        'payloads': attack.get_payloads(),
        'educational': attack.get_educational_content(),
    })


@app.route('/api/simulate', methods=['POST'])
def simulate():
    """Simulate a prompt input"""
    data = request.get_json()
    user_input = data.get('input', '')
    security_level = data.get('security_level', 'MEDIUM')

    # Set security level
    try:
        simulator.set_security_level(SecurityLevel[security_level])
    except KeyError:
        pass

    # Process input with timing and optional tracing
    start_time = time.time()

    if otel_manager:
        with otel_manager.trace_span("simulate_attack", {"security_level": security_level}):
            response, metadata = simulator.process_input(user_input)
    else:
        response, metadata = simulator.process_input(user_input)

    duration = time.time() - start_time

    # Record metrics
    metrics.record_request(duration, blocked=metadata.get('compromised', False))

    # Record OTel metrics
    if otel_manager:
        otel_manager.record_request("/api/simulate", "200", duration)
        if metadata.get('attacks_detected'):
            for attack in metadata['attacks_detected']:
                otel_manager.record_attack(
                    attack_type=attack['type'],
                    success=metadata.get('compromised', False),
                    detected=True,
                    duration=duration
                )

    if metadata.get('attacks_detected'):
        for attack in metadata['attacks_detected']:
            metrics.increment("web_attacks_detected", labels={"type": attack['type']})

    return jsonify({
        'response': response,
        'metadata': metadata,
    })


@app.route('/api/security-levels')
def get_security_levels():
    """Get available security levels"""
    levels = []
    for level in SecurityLevel:
        levels.append({
            'name': level.name,
            'value': level.value,
            'description': _get_level_description(level),
        })
    return jsonify(levels)


def _get_level_description(level: SecurityLevel) -> str:
    """Get description for security level"""
    descriptions = {
        SecurityLevel.NONE: "No protection - vulnerable to all attacks",
        SecurityLevel.LOW: "Basic keyword filtering only",
        SecurityLevel.MEDIUM: "Injection detection enabled",
        SecurityLevel.HIGH: "Advanced sanitization and blocking",
        SecurityLevel.MAXIMUM: "Full blocking on any detection",
    }
    return descriptions.get(level, "Unknown")


@app.route('/api/reset', methods=['POST'])
def reset():
    """Reset the simulator"""
    simulator.reset()
    metrics.reset()
    return jsonify({'status': 'ok', 'message': 'Simulator reset'})


@app.route('/api/metrics')
def get_metrics():
    """Get all monitoring metrics"""
    return jsonify(metrics.get_all_metrics())


@app.route('/api/metrics/attacks')
def get_attack_metrics():
    """Get attack-specific metrics"""
    return jsonify(metrics.get_attack_summary())


@app.route('/api/metrics/defenses')
def get_defense_metrics():
    """Get defense-specific metrics"""
    return jsonify(metrics.get_defense_summary())


@app.route('/api/metrics/prometheus')
def get_prometheus_metrics():
    """Export metrics in Prometheus format"""
    return metrics.export_prometheus(), 200, {'Content-Type': 'text/plain'}


@app.route('/api/dashboard/summary')
def get_dashboard_summary():
    """Get comprehensive dashboard summary"""
    attack_summary = metrics.get_attack_summary()
    defense_summary = metrics.get_defense_summary()
    status = simulator.get_status()

    return jsonify({
        'status': status,
        'attacks': attack_summary,
        'defenses': defense_summary,
        'uptime': metrics.get_all_metrics().get('uptime_seconds', 0),
        'timestamp': time.time()
    })


@app.route('/api/attack-types')
def get_attack_type_stats():
    """Get statistics broken down by attack type"""
    all_metrics = metrics.get_all_metrics()
    counters = all_metrics.get('counters', {})

    attack_types = ['prompt_injection', 'jailbreak', 'data_poisoning', 'model_extraction', 'membership_inference']
    stats = []

    for attack_type in attack_types:
        total_key = f'attacks_total{{attack_type={attack_type}}}'
        success_key = f'attacks_successful{{attack_type={attack_type}}}'
        detected_key = f'attacks_detected{{attack_type={attack_type}}}'

        total = counters.get(total_key, 0)
        successful = counters.get(success_key, 0)
        detected = counters.get(detected_key, 0)

        stats.append({
            'type': attack_type,
            'display_name': attack_type.replace('_', ' ').title(),
            'total': int(total),
            'successful': int(successful),
            'detected': int(detected),
            'success_rate': (successful / total * 100) if total > 0 else 0,
            'detection_rate': (detected / total * 100) if total > 0 else 0
        })

    return jsonify(stats)


@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'llm-attack-lab',
        'otel_enabled': OTEL_ENABLED,
    })


@app.route('/ready')
def ready():
    """Readiness check endpoint"""
    return jsonify({'status': 'ready'})


def run_web_server(host='0.0.0.0', port=8080, debug=None):
    """Run the web server"""
    # Use environment variable for debug mode, default to False in production
    if debug is None:
        debug = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'

    print(f"Starting LLM Attack Lab Dashboard on http://{host}:{port}")
    print(f"OpenTelemetry enabled: {OTEL_ENABLED}")
    if OTEL_ENABLED:
        print(f"Prometheus metrics available on port 8000")

    app.run(host=host, port=port, debug=debug)


if __name__ == '__main__':
    run_web_server()
