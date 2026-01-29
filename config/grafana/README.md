# Grafana - Observabilite Securite ML/LLM

## Vue d'ensemble

Ce dossier contient les dashboards et configurations Grafana pour la surveillance de securite des modeles ML et LLM. L'objectif est de detecter en temps reel les attaques adversariales, injections de prompts, tentatives d'extraction et autres menaces cyber.

---

## Architecture d'Observabilite

```
+------------------+     +-------------------+     +------------------+
|   Application    |---->|  OpenTelemetry    |---->| VictoriaMetrics  |
|   (Metriques)    |     |  Collector        |     |   (Stockage)     |
+------------------+     +-------------------+     +------------------+
        |                        |                         |
        v                        v                         v
+------------------+     +-------------------+     +------------------+
|   Prometheus     |     |   Alertmanager    |     |    Grafana       |
|   (Scraping)     |     |   (Alertes)       |     |  (Visualisation) |
+------------------+     +-------------------+     +------------------+
```

### Ports et Services

| Service          | Port  | Description                          |
|------------------|-------|--------------------------------------|
| Grafana          | 3000  | Interface de visualisation           |
| VictoriaMetrics  | 8428  | Stockage metriques (PromQL)          |
| OTel Collector   | 4317  | OTLP gRPC                            |
| OTel Collector   | 4318  | OTLP HTTP                            |
| OTel Prometheus  | 8889  | Export Prometheus                    |
| Application      | 8000  | Metriques applicatives               |

---

## Mapping Metriques <-> Types d'Attaques

### Matrice de Couverture Securite

Ce tableau permet de faire le lien entre les metriques Prometheus et les types d'attaques detectees :

| Metrique | Adversarial | Poisoning | Extraction | Prompt Injection | Jailbreak | Drift |
|----------|:-----------:|:---------:|:----------:|:----------------:|:---------:|:-----:|
| `ml_input_reconstruction_error` | X | | | | | |
| `ml_prediction_confidence_bucket` | X | | | | | |
| `ml_embedding_distance_to_centroid` | X | | | | | |
| `ml_prediction_stability_score` | X | | | | | |
| `ml_unstable_predictions_total` | X | | | | | |
| `ml_predictions_by_class_total` | | X | | | | X |
| `ml_prediction_distribution_psi` | | X | | | | X |
| `ml_api_queries_total` | | | X | | | |
| `ml_accuracy_by_class` | | X | | | | X |
| `llm_prompt_injection_score` | | | | X | X | |
| `llm_prompt_similarity_to_system` | | | X | X | | |
| `llm_output_policy_violations_total` | | | | | X | |
| `llm_tool_calls_total` | | | X | X | X | |

---

## Catalogue des Metriques

### Metriques Adversarial (Detection d'inputs malveillants)

#### `ml_input_reconstruction_error`
- **Type**: Histogram
- **Description**: Erreur de reconstruction autoencoder pour detection d'anomalies
- **Labels**: `model_name`, `input_type`
- **Seuil d'alerte**: > 2.5
- **Attaques detectees**: FGSM, PGD, inputs adversariaux
- **Panel Grafana**: "Input Reconstruction Error" (Section: Adversarial Detection)

```promql
# Percentile 95 de l'erreur de reconstruction
histogram_quantile(0.95, rate(ml_input_reconstruction_error_bucket[5m]))
```

#### `ml_prediction_confidence_bucket`
- **Type**: Histogram
- **Description**: Distribution des scores de confiance des predictions
- **Labels**: `model_name`, `predicted_class`
- **Seuil d'alerte**: > 0.95 avec erreur elevee
- **Attaques detectees**: Inputs adversariaux
- **Panel Grafana**: "Prediction Confidence Distribution" (Section: Adversarial Detection)

```promql
# Median de la confiance par classe
histogram_quantile(0.5, rate(ml_prediction_confidence_bucket[5m]))
```

#### `ml_embedding_distance_to_centroid`
- **Type**: Histogram
- **Description**: Distance des embeddings au centroide d'entrainement
- **Labels**: `model_name`, `layer`
- **Seuil d'alerte**: > 3x le seuil de base
- **Attaques detectees**: Out-of-distribution, Adversarial
- **Panel Grafana**: "Embedding Distance to Centroid" (Section: Adversarial Detection)

```promql
# Distance p95 avec seuil
histogram_quantile(0.95, rate(ml_embedding_distance_to_centroid_bucket[5m]))
ml_embedding_distance_threshold * 3
```

#### `ml_prediction_stability_score`
- **Type**: Gauge
- **Description**: Variance des predictions sous perturbations legeres
- **Labels**: `model_name`, `perturbation_type`
- **Seuil d'alerte**: Spike > 3x la moyenne
- **Attaques detectees**: Inputs adversariaux
- **Panel Grafana**: "Prediction Stability Score" (Section: Adversarial Detection)

```promql
ml_prediction_stability_score{model_name="$model"}
```

#### `ml_unstable_predictions_total`
- **Type**: Counter
- **Description**: Compteur des predictions qui ont change sous perturbation
- **Labels**: `model_name`, `perturbation_type`
- **Seuil d'alerte**: rate > 3x avg_over_time
- **Attaques detectees**: Inputs adversariaux
- **Panel Grafana**: "Unstable Predictions Rate" (Section: Adversarial Detection)

```promql
rate(ml_unstable_predictions_total[5m])
```

---

### Metriques Comportementales (Detection d'anomalies d'usage)

#### `ml_predictions_by_class_total`
- **Type**: Counter
- **Description**: Distribution des classes predites dans le temps
- **Labels**: `model_name`, `predicted_class`
- **Seuil d'alerte**: Changement soudain de distribution
- **Attaques detectees**: Data poisoning, Drift
- **Panel Grafana**: "Predictions by Class Distribution" (Section: Behavior Analysis)

```promql
rate(ml_predictions_by_class_total[5m])
```

#### `ml_prediction_distribution_psi`
- **Type**: Gauge
- **Description**: Population Stability Index / divergence KL pour detection de drift
- **Labels**: `model_name`, `reference_window`
- **Seuil d'alerte**: > 0.2 pendant 15min
- **Attaques detectees**: Data poisoning, Model drift
- **Panel Grafana**: "Distribution Drift (PSI)" (Section: Behavior Analysis)

```promql
ml_prediction_distribution_psi{reference_window="1d"}
```

#### `ml_api_queries_total`
- **Type**: Counter
- **Description**: Requetes API par utilisateur/IP pour rate limiting
- **Labels**: `user_id`, `ip_address`, `endpoint`
- **Seuil d'alerte**: > 100 req/10min par user
- **Attaques detectees**: Model extraction
- **Panel Grafana**: "API Queries per User (10min window)" (Section: Behavior Analysis)

```promql
sum by (user_id) (rate(ml_api_queries_total[10m])) * 600
```

#### `ml_accuracy_by_class`
- **Type**: Gauge
- **Description**: Precision par classe pour detecter les attaques ciblees
- **Labels**: `model_name`, `class_name`
- **Seuil d'alerte**: Chute > 10% vs baseline
- **Attaques detectees**: Targeted poisoning
- **Panel Grafana**: "Per-Class Accuracy vs Baseline" (Section: Behavior Analysis)

```promql
ml_accuracy_by_class{class_name="$class"}
ml_baseline_accuracy{class_name="$class"}
```

---

### Metriques LLM (Detection d'attaques specifiques LLM)

#### `llm_prompt_injection_score`
- **Type**: Histogram
- **Description**: Score du classifieur de detection d'injection (0-1)
- **Labels**: `model_name`, `detection_method`
- **Seuil d'alerte**: > 0.85
- **Attaques detectees**: Prompt injection, Jailbreak
- **Panel Grafana**: "Prompt Injection Score" (Section: LLM Security)

```promql
# Percentiles du score d'injection
histogram_quantile(0.50, rate(llm_prompt_injection_score_bucket[5m]))
histogram_quantile(0.95, rate(llm_prompt_injection_score_bucket[5m]))
histogram_quantile(0.99, rate(llm_prompt_injection_score_bucket[5m]))
```

#### `llm_prompt_similarity_to_system`
- **Type**: Histogram
- **Description**: Similarite embedding entre input utilisateur et system prompt
- **Labels**: `model_name`
- **Seuil d'alerte**: > 0.7
- **Attaques detectees**: System prompt extraction
- **Panel Grafana**: "System Prompt Similarity (Extraction Detection)" (Section: LLM Security)

```promql
histogram_quantile(0.95, rate(llm_prompt_similarity_to_system_bucket[5m]))
```

#### `llm_output_policy_violations_total`
- **Type**: Counter
- **Description**: Compteur de violations des politiques de contenu
- **Labels**: `model_name`, `violation_type`, `severity`
- **Seuil d'alerte**: Violations repetees
- **Attaques detectees**: Jailbreak
- **Panel Grafana**: "Policy Violations by Type" (Section: LLM Security)

```promql
rate(llm_output_policy_violations_total[5m])
sum(increase(llm_output_policy_violations_total[1h]))
```

#### `llm_tool_calls_total`
- **Type**: Counter
- **Description**: Appels d'outils/fonctions par nom, utilisateur et statut
- **Labels**: `tool_name`, `user_id`, `success`, `is_dangerous`
- **Seuil d'alerte**: > 5 appels/5min (shell/exec)
- **Attaques detectees**: Agent attacks, Prompt injection
- **Panel Grafana**: "Tool Calls by Name/User", "Tool Calls: Safe vs Dangerous" (Section: LLM Security)

```promql
sum by (tool_name, user_id) (rate(llm_tool_calls_total[5m])) * 300
sum by (is_dangerous) (increase(llm_tool_calls_total[1h]))
```

---

## Dashboards Grafana

### Dashboard 1: ML/LLM Security Metrics
**UID**: `ml-security-metrics`
**Fichier**: `dashboards/ml-security-metrics.json`

#### Sections et Panels

| Section | Panel ID | Panel | Metrique(s) Utilisee(s) |
|---------|----------|-------|-------------------------|
| Security Overview | 101 | Critical Alerts (1h) | `security_alerts_total{severity="critical"}` |
| Security Overview | 102 | Warning Alerts (1h) | `security_alerts_total{severity="warning"}` |
| Security Overview | 103 | Injection Score (p95) | `llm_prompt_injection_score_bucket` |
| Security Overview | 104 | Distribution PSI | `ml_prediction_distribution_psi` |
| Security Overview | 105 | Reconstruction Error (p95) | `ml_input_reconstruction_error_bucket` |
| Security Overview | 106 | Policy Violations (1h) | `llm_output_policy_violations_total` |
| Adversarial Detection | 201 | Input Reconstruction Error | `ml_input_reconstruction_error_bucket` |
| Adversarial Detection | 202 | Embedding Distance to Centroid | `ml_embedding_distance_to_centroid_bucket` |
| Adversarial Detection | 203 | Prediction Stability Score | `ml_prediction_stability_score` |
| Adversarial Detection | 204 | Unstable Predictions Rate | `ml_unstable_predictions_total` |
| Adversarial Detection | 205 | Prediction Confidence Distribution | `ml_prediction_confidence_bucket` |
| Behavior Analysis | 301 | Distribution Drift (PSI) | `ml_prediction_distribution_psi` |
| Behavior Analysis | 302 | Per-Class Accuracy vs Baseline | `ml_accuracy_by_class`, `ml_baseline_accuracy` |
| Behavior Analysis | 303 | Predictions by Class Distribution | `ml_predictions_by_class_total` |
| Behavior Analysis | 304 | API Queries per User (10min window) | `ml_api_queries_total` |
| LLM Security | 401 | Prompt Injection Score | `llm_prompt_injection_score_bucket` |
| LLM Security | 402 | System Prompt Similarity | `llm_prompt_similarity_to_system_bucket` |
| LLM Security | 403 | Policy Violations by Type | `llm_output_policy_violations_total` |
| LLM Security | 404 | Tool Calls by Name/User | `llm_tool_calls_total` |
| LLM Security | 405 | Tool Calls: Safe vs Dangerous | `llm_tool_calls_total` |
| Attack Coverage Matrix | 501 | Active Security Monitoring Coverage | Toutes les metriques |

### Dashboard 2: LLM Attack Lab
**UID**: `llm-attack-lab-main`
**Fichier**: `dashboards/llm-attack-lab.json`

Dashboard operationnel principal avec vue d'ensemble des attaques et defenses.

### Dashboard 3: Documentation
**UID**: `llm-attack-lab-docs`
**Fichier**: `dashboards/documentation.json`
**URL**: http://localhost:3000/d/llm-attack-lab-docs

Dashboard integrant toute la documentation du projet directement dans Grafana:
- README principal du projet
- Guide de demarrage rapide (Quick Start)
- Architecture et stack technologique
- Catalogue complet des metriques de securite
- Matrice de couverture attaques/metriques
- Regles d'alerting (critiques et warning)
- Guide de troubleshooting
- Best practices cyber/observabilite
- Exemples de requetes PromQL
- References et liens utiles

---

## Regles d'Alerting

Les alertes sont configurees dans `/config/prometheus/rules/security_alerts.yml`.

### Alertes Critiques

| Alerte | Condition | Severite |
|--------|-----------|----------|
| PromptInjectionDetected | `llm_prompt_injection_score > 0.85` | critical |
| PotentialAdversarialInput | `ml_input_reconstruction_error > 2.5` | critical |
| ModelDistributionDrift | `ml_prediction_distribution_psi > 0.2` pendant 15m | critical |
| SuspiciousToolUsage | `rate(llm_tool_calls_total{is_dangerous="true"}) > 5/5m` | critical |

### Alertes Warning

| Alerte | Condition | Severite |
|--------|-----------|----------|
| OutOfDistributionInput | `ml_embedding_distance_to_centroid > 3x threshold` | warning |
| SystemPromptExtractionAttempt | `llm_prompt_similarity_to_system > 0.7` | warning |
| SuspiciousQueryPattern | `rate(ml_api_queries_total) > 100/10m` | warning |
| PredictionInstabilitySpike | `ml_prediction_stability_score > 3x avg` | warning |

---

## Guide de Troubleshooting

### Probleme: Pas de donnees dans Grafana

1. **Verifier VictoriaMetrics**:
```bash
curl http://localhost:8428/api/v1/query?query=up
```

2. **Verifier les metriques de l'application**:
```bash
curl http://localhost:8000/metrics | grep -E "^(ml_|llm_)"
```

3. **Verifier OTel Collector**:
```bash
curl http://localhost:8889/metrics
```

### Probleme: Alertes non declenchees

1. Verifier que les metriques ont des donnees recentes
2. Verifier les labels dans les requetes PromQL
3. Consulter les logs Prometheus/Alertmanager

### Probleme: Metriques manquantes

Les metriques sont initialisees au demarrage avec des valeurs baseline. Si certaines metriques sont manquantes:

```python
from llm_attack_lab.monitoring import get_security_metrics
metrics = get_security_metrics()
metrics.initialize()
```

---

## Configuration Avancee

### Variables d'Environnement

| Variable | Description | Default |
|----------|-------------|---------|
| `PROMETHEUS_MULTIPROC_DIR` | Repertoire pour metriques multiprocess | `/tmp/prometheus` |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | Endpoint OTel | `http://localhost:4317` |
| `VICTORIAMETRICS_URL` | URL VictoriaMetrics | `http://localhost:8428` |

### Personnalisation des Seuils

Les seuils d'alerting peuvent etre ajustes via le code:

```python
from llm_attack_lab.monitoring import get_security_metrics

metrics = get_security_metrics()
metrics.set_threshold("llm_prompt_injection_score", 0.90)
metrics.set_threshold("ml_prediction_distribution_psi", 0.15)
metrics.set_embedding_threshold(4.0, model_name="production-model")
```

---

## Best Practices Cyber/Observabilite

### 1. Defense en Profondeur

- Combiner plusieurs metriques pour la detection
- Ne pas se fier a un seul indicateur
- Configurer des alertes a plusieurs niveaux (warning, critical)

### 2. Baseline et Contexte

- Toujours etablir une baseline avant de mettre en production
- Ajuster les seuils selon le contexte metier
- Documenter les seuils et leur justification

### 3. Correlation des Evenements

- Utiliser les labels pour correler les metriques
- Investiguer les patterns multi-metriques
- Exemple: `llm_prompt_injection_score` eleve + `llm_tool_calls_total{is_dangerous="true"}` = attaque probable

### 4. Retention et Forensics

- VictoriaMetrics retient 30 jours par defaut
- Exporter les alertes pour investigation long terme
- Logger les requetes suspectes pour analyse post-incident

### 5. Monitoring du Monitoring

- Surveiller la sante de la stack d'observabilite
- Alerter sur les pertes de metriques
- Verifier regulierement que les dashboards affichent des donnees

---

## Structure des Fichiers

```
config/grafana/
├── README.md                          # Ce fichier
├── dashboards/
│   ├── llm-attack-lab.json           # Dashboard operationnel
│   ├── ml-security-metrics.json      # Dashboard securite ML/LLM
│   └── documentation.json            # Documentation integree
└── provisioning/
    ├── dashboards/
    │   └── dashboards.yaml           # Configuration auto-chargement
    └── datasources/
        └── datasources.yaml          # Configuration sources de donnees
```

---

## References

- [OWASP Top 10 for LLM Applications](https://owasp.org/www-project-top-10-for-large-language-model-applications/)
- [MITRE ATLAS - Adversarial ML](https://atlas.mitre.org/)
- [Prometheus Best Practices](https://prometheus.io/docs/practices/naming/)
- [Grafana Dashboard Guidelines](https://grafana.com/docs/grafana/latest/dashboards/)

---

## Changelog

- **v1.0** - Creation initiale avec 13 metriques de securite
- **v1.1** - Ajout matrice de couverture attaques
- **v1.2** - Documentation complete du mapping Grafana
