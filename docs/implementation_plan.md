# Webdoc Uploader Web App Implementation Plan

We will build a simple, localized web application that provides a beautiful, user-friendly interface for uploading documents to Webdoc from your PC or network.

## Proposed Changes

We will build a full-stack local web application with the following components:

### 1. Backend Server (Python / Flask)
- Provide basic user authentication (e.g., a simple username and password) before accessing the upload functionality.
- Integrate the Webdoc production credentials (`api.txt`).
- Fetch and provide available **Document Types** and **Clinics** from Webdoc to the frontend.
- Handle receiving uploaded files from the browser, extracting the *personnummer* from the filenames, and pushing them to the Webdoc API.

#### [NEW] `app.py`
The main Flask server application handling standard web routes (`/login`, `/`, `/upload`, `/api/document_types`).

#### [NEW] `requirements_web.txt`
Dependencies needed to run the web app (e.g., `Flask`, `Flask-Login`, `requests`, `Werkzeug`).

### 2. Frontend App (HTML/Vanilla CSS/JS)
- **Design Philosophy**: As per best practices, the app will feature a premium, dynamic UI. It will incorporate a modern typography (e.g., Inter font), a sleek dark-mode layout or professional healthcare aesthetic, smooth hover transitions, and a clean drag-and-drop file upload area.
  
#### [NEW] `templates/login.html`
A polished login page to secure the application.

#### [NEW] `templates/dashboard.html`
The main dashboard where the user can:
1. View the connection status to Webdoc Production.
2. Select a target **Document Type** from a dynamically populated dropdown menu.
3. Drag-and-drop or select single/multiple files for batch uploading.
4. View a live progress report and final summary of successful vs. failed uploads.

#### [NEW] `static/style.css` & `static/app.js`
The styling and dynamic client-side logic handling the drag-and-drop UI and API requests to our Flask backend.

## Open Questions

1. **Authentication**: For the "basic login", would you like a single hardcoded username/password (e.g., `admin` / `password123`) that you can change in the code, or a small `users.json` file to manage multiple accounts?
2. **Network Access**: Do you plan to run this just on your local PC (accessible only on `localhost`), or should it be configured to be accessible by other computers on your office network?
3. **Personnummer Format**: For batch uploads through this web interface, we will assume the patient's personnummer is still embedded in the filename (like `19121212-1212.jpg`). Is that correct?

## Verification Plan
1. Install requirements: `pip install -r requirements_web.txt`.
2. Start the local server: `python app.py`.
3. Navigate to `http://localhost:5000` in the browser.
4. Verify the user login process.
5. Verify the Webdoc API connects and populates the document types dropdown.
6. Test uploading a file through the UI to ensure it securely creates a record in Webdoc.
