# Feature Roadmap

## Implemented Features ✓

### 5. Verschiedene Chunking-Strategien ✓
- [x] Character-based chunking (original)
- [x] Paragraph-based chunking
- Semantisches Chunking (nach Absätzen/Sätzen)
- Hierarchisches Chunking möglich als Erweiterung

### 4. Inkrementelle Updates ✓
- [x] Prüfung ob Dokument bereits verarbeitet wurde (SHA256 hash)
- [x] Nur geänderte/neue Dokumente verarbeiten
- [x] Update-Strategie für modifizierte Dokumente
- [x] Automatisches Löschen alter Chunks bei Änderungen

## Planned Features

### 1. Semantic Search / Query-Funktion
- Möglichkeit, Fragen zu stellen und ähnliche Chunks zu finden
- Nutzt die bereits gespeicherten Embeddings für Ähnlichkeitssuche
- Ausgabe der relevantesten Textpassagen mit Scores
- **Implementierungsaufwand**: Mittel
- **Nutzen**: Hoch - macht die Embeddings nutzbar

### 2. Batch-Verarbeitung
- Mehrere Dokumente auf einmal verarbeiten (ganzer Ordner)
- Progress-Bar für längere Prozesse
- Zusammenfassendes Reporting
- **Implementierungsaufwand**: Niedrig
- **Nutzen**: Hoch - spart Zeit bei vielen Dokumenten

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

### 7. CLI mit Argumenten
- Argparse für flexible Kommandozeilennutzung
- Verschiedene Modi (embed, search, status)
- **Implementierungsaufwand**: Niedrig
- **Nutzen**: Mittel - bessere Usability

### 8. Logging & Monitoring
- Strukturiertes Logging in Datei
- Statistiken über verarbeitete Dokumente
- Fehlerbehandlung mit Retry-Logik
- **Implementierungsaufwand**: Niedrig
- **Nutzen**: Mittel - besseres Debugging

### 9. Web-Interface
- Einfaches FastAPI/Flask Frontend
- Upload-Interface für Dokumente
- Search-Interface
- **Implementierungsaufwand**: Hoch
- **Nutzen**: Hoch - deutlich bessere UX

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

### Quick Wins (geringer Aufwand, hoher Nutzen):
1. **Batch-Verarbeitung** - macht das Tool viel praktischer
2. **CLI mit Argumenten** - bessere Developer Experience
3. **Logging & Monitoring** - hilfreich für Debugging

### High Impact (mittlerer Aufwand, sehr hoher Nutzen):
1. **Semantic Search / Query-Funktion** - macht Embeddings nutzbar
2. **RAG System** - vollständiges QA-System

### Nice to Have:
1. Web-Interface - wenn GUI gewünscht
2. Weitere Dokumentformate - je nach Bedarf
3. OCR-Support - für spezielle Anforderungen