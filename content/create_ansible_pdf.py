from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm

def create_ansible_pdf():
    pdf_file = "created/ansible_info.pdf"
    c = canvas.Canvas(pdf_file, pagesize=A4)
    width, height = A4

    # title
    c.setFont("Helvetica-Bold", 24)
    c.drawString(2*cm, height - 3*cm, "Ansible")

    # footer
    c.setFont("Helvetica-Bold", 14)
    c.drawString(2*cm, height - 4.5*cm, "Automatisierung leicht gemacht")

    # main text
    c.setFont("Helvetica", 11)

    text_content = """
Ansible ist ein Open-Source-Automatisierungstool, das von Red Hat entwickelt wird.
Es ermoeglicht die Automatisierung von IT-Aufgaben wie Konfigurationsmanagement,
Anwendungsbereitstellung und Orchestrierung.

Hauptmerkmale von Ansible:

- Agentenlos: Ansible benoetigt keine Agenten auf den Zielmaschinen. Es verwendet
  SSH fuer die Kommunikation mit Linux/Unix-Systemen und WinRM fuer Windows.

- Deklarativ: Mit Ansible beschreiben Sie den gewuenschten Zustand Ihrer Infrastruktur
  in YAML-Dateien, sogenannten Playbooks.

- Idempotent: Ansible stellt sicher, dass mehrfache Ausfuehrungen desselben Playbooks
  immer zum gleichen Ergebnis fuehren.

- Einfache Syntax: YAML-basierte Playbooks sind leicht lesbar und verstaendlich,
  auch fuer Einsteiger.

Wichtige Konzepte:

1. Inventory: Eine Liste der zu verwaltenden Server und deren Gruppierung.

2. Playbooks: YAML-Dateien, die Aufgaben und deren Reihenfolge definieren.

3. Roles: Wiederverwendbare Sammlungen von Aufgaben, Variablen und Templates.

4. Modules: Vorgefertigte Funktionen fuer spezifische Aufgaben wie Dateiverwaltung,
   Paketverwaltung oder Cloud-Ressourcen.

Ansible ist ideal fuer DevOps-Teams, die ihre Infrastruktur als Code verwalten
moechten (Infrastructure as Code). Es integriert sich nahtlos mit CI/CD-Pipelines
und unterstuetzt eine Vielzahl von Cloud-Plattformen wie AWS, Azure und Google Cloud.
"""

    # Text in Zeilen aufteilen und zeichnen
    y_position = height - 6*cm
    line_height = 0.5*cm

    for line in text_content.strip().split('\n'):
        if y_position < 2*cm:
            break
        c.drawString(2*cm, y_position, line.strip())
        y_position -= line_height

    c.save()
    print(f"PDF erstellt: {pdf_file}")

if __name__ == "__main__":
    create_ansible_pdf()
