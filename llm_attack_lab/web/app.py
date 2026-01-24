"""
Web Dashboard for LLM Attack Lab

Provides a visual interface for exploring and simulating LLM attacks.
"""

import json
from flask import Flask, render_template, request, jsonify
from llm_attack_lab.core.llm_simulator import LLMSimulator, SecurityLevel
from llm_attack_lab.attacks import ATTACK_REGISTRY

app = Flask(__name__, template_folder='templates', static_folder='static')

# Global simulator instance
simulator = LLMSimulator()


@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('index.html')


@app.route('/api/status')
def get_status():
    """Get current simulator status"""
    return jsonify(simulator.get_status())


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

    # Process input
    response, metadata = simulator.process_input(user_input)

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
    return jsonify({'status': 'ok', 'message': 'Simulator reset'})


def run_web_server(host='0.0.0.0', port=8080, debug=True):
    """Run the web server"""
    print(f"Starting LLM Attack Lab Dashboard on http://{host}:{port}")
    app.run(host=host, port=port, debug=debug)


if __name__ == '__main__':
    run_web_server()
