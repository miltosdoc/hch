# Webdoc Upload Portal
**Producent:** Hjärtcentrum Halland  
**Version:** 1.0  
**Typ:** Intern Webbadministration / API Integrationsportal  

---

## 1. Systemöversikt
Webdoc Upload Portal är en skräddarsydd, lokal webbapplikation utvecklad för Hjärtcentrum Halland. Syftet med applikationen är att automatisera, validera och batch-uppladda inkommande remisser och patientdokument till Webdoc EMR-systemet via deras officiella API.

Applikationen ersätter manuell inmatning med ett effektivt "Drag-and-Drop" gränssnitt som automatiskt:
- Identifierar patienter via filnamn.
- Grupperar flersidiga dokument.
- Kopplar dokumenten till rätt vårdgivare (Miltiadis Triantafyllou).
- Validerar personnummer mot Webdoc-registret före uppladdning för att förhindra felaktig journalföring.

## 2. Huvudfunktioner
* **Drag-and-Drop Batching:** Användare kan dra in tiotals eller hundratals inskannade remisser till webbläsaren för parallell uppladdning.
* **Smart Filnamnsigenkänning:** Systemet använder regex för att extrahera personnummer (både 10- och 12-siffriga) direkt ur filnamnet (ex. `19410712-9423.jpg`).
* **Automatisk PDF-sammanslagning:** Om flera filer delar samma personnummer men styrs av suffix (ex. `194107129423A.jpg` och `194107129423B.jpg`), slår systemet automatiskt ihop dessa till ett enda, välorganiserat flersidigt PDF-dokument i rätt ordning innan uppladdning.
* **Smart Dokumenttypsval:** Systemet prioriterar automatiskt dokumenttypen **"RemissBot"** (alternativt "Inreferral" / "Remiss") vid uppladdning av externa remisser.
* **Säkerhetsfokus:** Filerna tvättas bort (rensas) från den lokala servern direkt efter att de skickats och en lyckad signal bekräftats.

## 3. Tekniska Specifikationer
* **Backend:** Python 3.x, Flask (Webbramverk)
* **API Klient:** `requests` för OAuth 2.0 Client Credentials kommunikation via `api.atlan.se`.
* **Bild- & PDF Bearbetning:** `Pillow` och `img2pdf` för lossless-konvertering format till rigorösa PDF-standarder (förhindrar Webdoc 500-errors).
* **Frontend:** Vanilla JavaScript, HTML5, specialbyggd CSS (Glassmorphism & Medical Deep Blue).

## 4. Konfiguration & Säkerhet
Applikationen kräver följande filer i sin rotmapp för att fungera:
1. `api.txt`: Innehåller referenser till Webdoc API Production.  
   - **Rad 1:** *Client ID*  
   - **Rad 2:** *Client Secret*
2. `users.json`: Innehåller inloggningsuppgifter för att överhuvudtaget nå portalen internt.
   ```json
   {
       "admin": "ditt_valda_lösenord"
   }
   ```

*(Observera: Dessa filer får aldrig delas eller läggas upp i en publik kodbank!)*

## 5. Drift- & Startinstruktioner

### Förberedelser (En gång)
Om maskinen är ny, säkerställ att Python är installerat samt biblioteken som applikationen förlitar sig på skapas:
```bash
pip install flask flask_login requests pillow img2pdf werkzeug
```

### Starta Portalen
1. Öppna mappen WebdocAPI på servern eller din lokala dator.
2. Öppna en kommandotolk (Terminal/PowerShell) i denna mapp.
3. Kör kommandot:
   ```bash
   python app.py
   ```
4. Öppna en webbläsare (Google Chrome/Edge) och gå till: `http://localhost:5000` (om du sitter vid servern).

### Åtkomst från andra datorer (Webbåtkomst)
För att dina kollegor ska kunna ladda upp remisser från en annan dator på nätverket:
1. Skriv in den här datorns IP-adress i webbläsaren följt av port 5000:
   `http://10.100.11.88:5000`
2. Observera att Windows Brandvägg på denna dator kan behöva konfigureras för att **tillåta inkommande trafik på port 5000** om den blockerar anslutningen.

## 6. Felsökning (Vanliga Felkoder)
* **Patient med PN hittades inte (404):** Filnamnet innehåller ett personnummer som ännu inte existerar i Hjärtcentrum Hallands Webdoc-miljö. Skapa patienten i Webdoc och försök igen.
* **Auth Failed / API Offline:** `api.txt` saknas, innehåller fel värden, eller så har brandväggen blockerat utgående tillgång till `auth.atlan.se`.
* **Upload Failed (500):** Kan ibland uppstå om Webdocs mottagande servrar har driftstörningar, eller om den uppladdade bilden är korrupt. Felet loggas direkt i gränssnittet.

---
**Äganderätt & Underhåll**  
Denna kodbas och tillhörande arbetsflöden har tagits fram specifikt för integrering av remisshantering för Hjärtcentrum Halland. Vid ytterligare dokumentstrukturer krävs uthyrd certifierad tillgång till Webdoc SE via Carasent AB.
