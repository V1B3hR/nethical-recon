# 🌐 MAPA ROZWOJU NETHICAL‑RECON 5.0 (12–18 miesięcy)

_Focus:_ Reconnaissance | Stabilność | Jakość Kodów | Praktyki OWASP/CISA | Platformizacja | Automatyzacja

---

## I. FUNDAMENTY & BEZPIECZEŃSTWO (0–3 miesiące) ✅ COMPLETE

**Status:** ✅ IMPLEMENTED (2026-01-08)  
**Summary:** [PHASE_ROADMAP5_I_SUMMARY.md](PHASE_ROADMAP5_I_SUMMARY.md)

### 🔧 1. Stabilność i jakość kodu ✅
- ✅ 100% pokrycie testami jednostkowymi i integracyjnymi (pytest, coverage).
- ✅ Codzienny CI/CD (GitHub Actions, automatyczny linting, testy, security scanning).
- ✅ Stosowanie static analysis (Python: mypy, bandit, safety, Rust: clippy, cargo-audit).
- ✅ Refaktoryzacja pod czystą architekturę (ports & adapters, dependency injection).
- ✅ Pre-commit hooks, formatowanie kodu (black, isort).

### 📚 2. Zgodność z OWASP (podstawy) ✅
- ✅ Implementacja wymagań OWASP ASVS (poziom 1–2).
- ✅ Secure coding guidelines i przeglądy kodu pod kątem bezpieczeństwa.
- ✅ Walidacja, sanitizacja i typowanie danych wejściowych (zgodność z OWASP Top 10: Injection, SSRF, Validation, Security Logging).

### 🛰️ 3. Pasywny Reconnaissance ✅
- ✅ Moduły pasywnego reconu: DNS, WHOIS, certyfikaty, subdomeny, ASN, IP ranges.
- ✅ Integracje z publicznymi źródłami OSINT (crt.sh, SecurityTrails, Shodan).
- ✅ Pluginowa warstwa sensorów OSINT (łatwa rozbudowa).
- ✅ Moduł alertingu (webhook, e‑mail, Slack, Discord).

---

## II. ROZBUDOWA SILNIKA & INTELIGENCJI (3–6 miesięcy)

### 🕸️ 4. Attack Surface Mapping — warstwa 1 (fingerprinting)
- Mapowanie hostów/usług, wykrywanie technologii, CMS, frameworków.
- Analiza portów/protokołów (pasywna + półaktywna).
- Automatyczne baseline zasobów: pierwszy obraz powierzchni ataku.

### 🧠 5. Threat Intelligence Enrichment
- Integracje z AbuseIPDB, OTX, GreyNoise, VirusTotal, etc.
- Risk scoring hostów/assetów (moduł score/alert).
- Korelacja danych i enrichment pluginowy.
- Plugin API umożliwiający podłączenie własnych źródeł threat feed.

### 🧱 6. Kod klasy Enterprise
- Kontrakty API (OpenAPI 3.x, testy kontraktowe).
- Hermetyzacja logicznych domen, izolacja błędów.
- Wprowadzenie pełnego dependency injection.
- Testy obciążeniowe, fuzzing, chaos engineering (zgodność z OWASP WSTG).
- Modularny system notyfikacji/alertów.
- Async I/O ready – refaktoryzacja core na asynchroniczność.

---

## III. ARCHITEKTURA OPERACYJNA (6–12 miesięcy)

### 🛰️ 7. Aktywny Recon (warstwa 2)
- Aktywne skanowanie portów (Nmap/Python/Rust High-Performance).
- Banner grabbing, advanced protocol probing.
- TLS fingerprinting (JA3/JA4), identyfikacja wersji i mapping do CVE.
- Obsługa pluginów drono-sensorów i live asset mapping.

### 🗺️ 8. Attack Surface Mapping — warstwa 2
- Generowanie i wizualizacja grafu zależności (host→usługa→technologia→podatność).
- Wykrywanie, alertowanie i różnicowanie zmian (delta/baseline).
- Exposed assets detection oraz trending assets.
- Alerty live na nowe incydenty i “delta monitoring”.

### 🛡️ 9. OWASP i audyt bezpieczeństwa — poziom zaawansowany
- OWASP WSTG (Web Security Testing Guide) – wybrane testy bezpieczeństwa.
- Automatyczne checklisty audytowe, generatory raportów zgodności (PCI DSS, GDPR, etc).
- Moduł testów bezpieczeństwa API (OWASP API Top 10), security logging.
- Monitoring i SIEM-ready logging; webhooki, syslog, integracja alertów.

### 💬 Dodatki ENTERPRISE
- System alertowania: e‑mail, webhook, ServiceNow/JIRA integration.
- Wstępna multi-tenancy (workspace separation).
- Early-stage plugin marketplace (własne pluginy, rozliczanie, review system).

---

## IV. PLATFORMIZACJA & UI/UX (12–18 miesięcy)

### 📊 10. Dashboard / GUI
- Webowe UI (Tauri+Rust, React/Next.js, D3.js grafy).
- Wizualizacja grafowa assetów, timeline reconu.
- Live monitoring assetów, findings, jobs, alertów.
- Moduł raportów (PDF/HTML, client-ready reporting).

### 🤖 11. System agentów i automatyzacji
- Harmonogramy rozpoznania (playbooki, orchestrator, job dependencies).
- Automatyczne playbooki (“pełny recon domeny”, “alert escalation”, “incident response”).
- Pełna integracja SIEM/SOAR (Elastic, Splunk, Azure Sentinel, webhooki).

### 🧬 12. Nethical Integration Layer
- Wspólne API pod integracje z innymi narzędziami Nethical.
- Centralne API scoringu i decision engine.
- Możliwość organizowania ekosystemu narzędzi (plugin registry, extension API).

### 🔌 13. Extension & Marketplace
- Publiczny marketplace na pluginy custom (zatwierdzanie, review, versioning).
- Extension API dla społeczności.

---

## V. WERSJA ENTERPRISE & GLOBAL INTELLIGENCE (18+ miesięcy)

### 🏢 14. Zaawansowane funkcje bezpieczeństwa i core intelligence
- Anomaly detection (ML, baseline, outlier analysis).
- Wykrywanie lateral movement, chain analysis, kill chain detection.
- Integracja z firmowym asset inventory i CMDB.

### 🌍 15. Globalny Attack Surface Intelligence
- Skanowanie całych organizacji (subdomain enumeration, cloud asset discovery).
- Pełna obsługa multi-cloud (AWS/GCP/Azure, shadow IT detector).
- Mapping risk i “organization digital twin”.
- Integracja z MITRE ATT&CK/TTP mapping.

---

## VI. CISA-COMPLIANCE & INTEGRATION (równolegle, ulepszane na każdym etapie)

### 🏛️ 16. Integracja wytycznych i alertów CISA

- **Integracja katalogu CISA Known Exploited Vulnerabilities (KEV) do scoringu podatności, alertowania i dashboardu.**
- **Automatyczny feed alertów i wytycznych CISA (RSS/API/alerts). Oznaczenia i statusy “Shields Up” w dashboardzie.**
- **Tryb polityki skanowania zgodnej z CISA (CISA Policy Mode) – predefiniowane profile, rekomendowane testy, alerty, typowanie assetów.**
- **Raporty PDF/HTML z checklistą CISA compliance i dedykowanymi sekcjami KEV/alert mappingu.**
- **Dedykowane pluginy „CISA BOD Checker” dla instytucji publicznych/federalnych.**
- **Mapowanie scoringu i alertów do wytycznych/kategorii CISA (automatyczny dashboard coverage).**
- **Monitoring i alertowanie coverage rekomendowanych przez CISA obszarów attack surface.**
- **Update scenariuszy SOAR/playbooków w zgodzie z najnowszymi zaleceniami CISA.**

---

## BONUS: Propozycje długoterminowe (`24m+`)
- **Composable Analytics** – generatory dashboardów (drag&drop).
- **Pełna asynchroniczność i obsługa event streamów (np. Kafka, NATS)**.
- **Obecność w publicznych repozytoriach compliance & integracje z narzędziami audytorskimi.**

---

## OGÓLNE KIERUNKI I WYTYCZNE

- **Security First**: Każdy feature zgodny z zasadami secure development, OWASP, CISA.
- **Testability**: Testy i kontrakty przed integracją.
- **Open API/Plugin**: Wszystko rozszerzalne, dokumentowane (Extension API).
- **Automatyzacja**: Łatwa integracja z pipeline CI/CD oraz automatyzatory (Ansible, Terraform, SOAR).
- **Compliance-driven**: Wersja dojrzała zawsze uwzględnia wytyczne CISA, OWASP, NIST, MITRE.

---

Wersja: Roadmap 5.0 / 2026  
Maintainer: V1B3hR  
Feedback i propozycje: issues / discussions / roadmap review  
