Project created by bootstrap.py

How to run:

1) Create virtual environment (recommended)
   python -m venv venv
   Windows: venv\Scripts\activate
   macOS/Linux: source venv/bin/activate

2) Install dependencies:
   pip install -r requirements.txt

3) Run the app:
   uvicorn main:app --reload --host 0.0.0.0 --port 8000

4) Open in browser:
   http://127.0.0.1:8000/login   -> Login page (admin:admin123, director:dir123)
   After login as admin: / -> Form
   As director: /director -> Pending list
   /dashboard -> All documents

Features:
 - Login required for admin and director roles
 - Admin creates expense report with fixed 10-row table
 - Automatic lines for empty fields and empty table rows
 - Director views full document before signing/approving in the same format
 - Signatures with pen-like style (thickness, color)
 - Dashboard with sorted documents by doc_number
 - View page for reading documents
 - PDF generation on approval to reduce editability; use PDF for printing; no Word downloads
 - Monthly archiving
 - Document fits one A4 page
 - Signatures placed inline without shifting positions

Files/folders created:
 - app.py (FastAPI backend)
 - templates/index.html, director.html, dashboard.html, error.html, login.html, view.html
 - static/style.css, signature_pad.min.js
 - documents/ (.docx/.pdf)
 - signatures/ (PNG signatures)
 - json/documents.json, users.json
 - archive/ (archives)

This bootstrap creates a secure e-signature system for expense reports.
