# Feature Roadmap

## Implemented Features ✓

### 7. CLI mit Argumenten ✓
- [x] Argparse für flexible Kommandozeilennutzung
- [x] Verschiedene Modi (embed, search, status, delete)
- [x] Delete-Command mit Bestätigungsprompt und Force-Option
- [x] Batch-Verarbeitung von Dokumenten
- [x] Verzeichnis-Verarbeitung
- [x] Überschreiben von .env-Einstellungen via CLI

### 5. Verschiedene Chunking-Strategien ✓
- [x] Character-based chunking (original)
- [x] Paragraph-based chunking
- [x] Semantisches Chunking (embedding-basiert mit konfigurierbarem Similarity Threshold)
- [ ] Hierarchisches Chunking möglich als Erweiterung

### 4. Inkrementelle Updates ✓
- [x] Prüfung ob Dokument bereits verarbeitet wurde (SHA256 hash)
- [x] Nur geänderte/neue Dokumente verarbeiten
- [x] Update-Strategie für modifizierte Dokumente
- [x] Automatisches Löschen alter Chunks bei Änderungen

### 1. Semantic Search / Query-Funktion ✓ (Teilweise)
- [x] Möglichkeit, Fragen zu stellen und ähnliche Chunks zu finden
- [x] Nutzt die bereits gespeicherten Embeddings für Ähnlichkeitssuche
- [x] Ausgabe der relevantesten Textpassagen mit Scores
- [x] Unterstützt sowohl Supabase als auch PostgreSQL
- [x] Optimiert mit pgvector wenn verfügbar
- [ ] Erweiterte Filterung und Ranking (für spätere Iteration)

### 9. Web-Interface ✓
- [x] FastAPI Backend mit REST API
- [x] Upload-Interface für Dokumente (Drag & Drop)
- [x] Echtzeit-Progress-Tracking mit Polling
- [x] Search-Interface mit konfigurierbarem Result-Limit
- [x] Dokumenten-Verwaltung (Liste, Löschen)
- [x] Settings-Anzeige (read-only)
- [x] Responsive Design mit Vanilla JavaScript (kein Build-Step)
- [x] Background-Task-Verarbeitung
- [x] Support für beide Storage-Backends (Supabase & PostgreSQL)
- [ ] WebSocket für Real-Time Updates (geplant)
- [ ] Batch-Upload mehrerer Dateien (geplant)

### 2. Batch-Verarbeitung ✓ (Teilweise)
- [x] Mehrere Dokumente auf einmal verarbeiten (ganzer Ordner)
- [x] Zusammenfassendes Reporting
- [x] Progress-Tracking im Web-Interface
- [ ] Progress-Bar für CLI (geplant)
- **Implementierungsaufwand**: Niedrig
- **Nutzen**: Hoch - spart Zeit bei vielen Dokumenten

## Planned Features

### 3. Metadaten-Tracking (teilweise implementiert)
- [x] Zeitstempel wann Dokument verarbeitet wurde
- [x] Datei-Hash zur Erkennung von Duplikaten
- [ ] Dateigröße, Seitenzahl, etc.
- [ ] Custom Metadaten (Tags, Kategorien)
- **Implementierungsaufwand**: Niedrig
- **Nutzen**: Mittel

### 6. RAG (Retrieval Augmented Generation)
- Integration mit LLM für Frage-Antwort
- Kontext aus relevanten Chunks nutzen
- Quellenangaben in Antworten
- **Implementierungsaufwand**: Mittel-Hoch
- **Nutzen**: Sehr Hoch - vollständiges QA-System

### 8. Logging & Monitoring
- Strukturiertes Logging in Datei
- Statistiken über verarbeitete Dokumente
- Fehlerbehandlung mit Retry-Logik
- **Implementierungsaufwand**: Niedrig
- **Nutzen**: Mittel - besseres Debugging

### 10. Weitere Dokumentformate
- Markdown, HTML, CSV
- PowerPoint (PPTX)
- Excel mit Tabellenerkennung
- **Implementierungsaufwand**: Mittel
- **Nutzen**: Mittel - mehr Flexibilität

### 11. OCR-Support
- Bildbasierte PDFs verarbeiten
- Integration mit Tesseract oder Cloud OCR
- **Implementierungsaufwand**: Mittel-Hoch
- **Nutzen**: Mittel - für spezielle Use Cases wichtig

## Prioritäten-Empfehlung

### Completed ✓:
1. ✓ **Batch-Verarbeitung** - macht das Tool viel praktischer
2. ✓ **CLI mit Argumenten** - bessere Developer Experience
3. ✓ **Semantic Search / Query-Funktion** - macht Embeddings nutzbar
4. ✓ **Web-Interface** - deutlich bessere UX mit GUI

### Quick Wins (geringer Aufwand, hoher Nutzen):
1. **Logging & Monitoring** - hilfreich für Debugging
2. **WebSocket für Web-Interface** - noch besseres Real-Time Feedback

### High Impact (mittlerer Aufwand, sehr hoher Nutzen):
1. **RAG System** - vollständiges QA-System
2. **Erweiterte Metadaten** - bessere Filterung und Organisation

### Nice to Have:
1. Weitere Dokumentformate - je nach Bedarf
2. OCR-Support - für spezielle Anforderungen
3. Batch-Upload im Web-Interface - mehrere Dateien gleichzeitig