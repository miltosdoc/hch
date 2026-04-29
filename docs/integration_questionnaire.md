# Integration Description Questionnaire - Webdoc API

---

## 1. Background

Vi driver en specialistvårdsmottagning (Hjärtcentrum Halland) och har två behov som motiverar integration med Webdoc API:t:

**Dokumentuppladdning:** Remisser och andra medicinska dokument skannas och behöver laddas upp till rätt patientakt i Webdoc. Idag sker detta manuellt, vilket är tidskrävande och felbenäget. Vi behöver en automatiserad lösning som matchar inskannade filer mot patienter via personnummer och laddar upp dem som dokumentposter.

**Statistikuttag av väntetider:** Vi arbetar med att ta fram statistik över våra väntetider inför en kommande granskning där vi behöver redogöra för verksamhetens siffror. När remisser skannas och laddas upp hamnar de i väntelistan; detta datum sammanfaller med inremissdatumet. Eftersom majoriteten av våra patienter omfattas av vårdgarantin registrerar vi även betalningsförbindelser med start- och slutdatum. Vi har ett kritiskt behov av att extrahera dessa datum (registreringsdatum samt datum för betalningsförbindelse) för rapportering. De nuvarande CSV-exportmallarna i Webdoc saknar valbara fält för dessa datapunkter, vilket gör det omöjligt att generera nödvändiga rapporter via det vanliga gränssnittet. Via API:t kan vi hämta bokningsdata med tillhörande datum, patienttyper och betalningsinformation för att sammanställa den statistik som krävs inför granskningen.

---

## 2. Description of the Solution

Integrationen består av två arbetsflöden:

### Arbetsflöde 1: Dokumentuppladdning (batch)
1. Medicinska dokument (remisser, bilder, PDF:er) skannas och placeras i en lokal mapp.
2. Systemet autentiserar mot Webdoc API med client credentials (POST /oauth/token).
3. Kliniker och dokumenttyper hämtas (GET /v1/clinics, GET /v1/documentTypes).
4. Personnummer extraheras automatiskt från filnamnen.
5. Varje patient slås upp i Webdoc (GET /v2/patients).
6. Dokumentet laddas upp till patientens akt på rätt klinik (POST /v1/clinics/{clinicId}/documents).
7. Uppladdade filer flyttas till en "processed"-mapp.

### Arbetsflöde 2: Statistikuttag
1. Systemet autentiserar mot Webdoc API (POST /oauth/token).
2. Bokningsdata hämtas för en given tidsperiod (GET /v1/bookings) med filter för klinik, datumintervall och patienttyp.
3. Data aggregeras och sammanställs lokalt: registreringsdatum, bokningsdatum, patienttyp (kopplat till betalningsförbindelse) och relaterad betalningsinformation.
4. Patienttyper hämtas vid behov (GET /v1/patientTypes) för att koppla patienttypens ID till dess namn/typ (t.ex. vårdgaranti, betalningsförbindelse).
5. Resultaten exporteras till rapportformat (CSV/Excel) för intern analys och presentation vid granskning.

---

## 3. Webdoc API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/oauth/token` | POST | OAuth2-autentisering (hämta access token) |
| `/v1/clinics` | GET | Hämta lista över kliniker (klinik-ID) |
| `/v1/documentTypes` | GET | Hämta tillgängliga dokumenttyper |
| `/v2/patients` | GET | Slå upp patient via personnummer |
| `/v1/clinics/{clinicId}/documents` | POST | Ladda upp dokument till patientakt |
| `/v1/bookings` | GET | Hämta bokningsdata (datum, patienttyp, betalningsinfo) |
| `/v1/bookings` | POST | Skapa bokning |
| `/v1/bookings` | PATCH | Uppdatera bokning |
| `/v1/bookings` | DELETE | Ta bort bokning |
| `/v1/bookingTypes` | GET | Hämta bokningstyper |
| `/v1/patientTypes` | GET | Hämta patienttyper (privat, betalningsförbindelse, etc.) |
| `/v1/patientTypes/{id}` | GET | Hämta patienttyp per ID |
| `/v1/notes` | POST | Skapa anteckning |
| `/v1/visits/{visitId}/records` | PATCH | Lägg till journaldata i anteckning/besök |
| `/v1/actionCodes` | GET | Hämta åtgärdskoder (KVÅ) |
| `/v1/users` | GET | Hämta användare/vårdgivare (referens vid uppladdning) |
| `/v1/clinics/{clinicId}/visits` | GET | Hämta besöksdata |
| `/v1/visits/{visitId}/recordSignatures` | POST | Signera journalanteckning |

---

## 4. Webdoc API Scopes

| Scope | Purpose |
|-------|---------|
| `documents:write` | Ladda upp dokument till patientakter |
| `document-types:read` | Läsa tillgängliga dokumenttyper |
| `clinics:read` | Läsa klinikinformation |
| `patient:read` | Slå upp patientdata via personnummer |
| `patient:write` | Skapa anteckningar och journaldata |
| `bookings:read` | Läsa bokningsdata för statistikuttag |
| `bookings:write` | Hantera bokningar |
| `patient-types:read` | Läsa patienttypdefinitioner |
| `actioncodes:read` | Läsa åtgärdskoder |
| `users:read` | Läsa användardata (vårdgivare) |
| `record-signatures:write` | Hantera signaturer på journalanteckningar |
| `self-service` | Läsa besöksdata (GET /v1/clinics/{clinicId}/visits) |

---

## 5. Webdoc API Grant Types

**Grant type:** `client_credentials`

Integrationen körs som en server-till-server-applikation (Python-skript) utan slutanvändarinteraktion i webbläsare, varför grant type `client_credentials` används. Ingen redirect URI behövs.

Token-endpoint:
- Integration: `https://auth-integration.carasent.net/oauth/token`
- Produktion: `https://auth.atlan.se/oauth/token`

---

## 6. External Links ("uthopp")

Integrationen använder inga externa länkar. Det är en backend-integration (Python-skript) utan användargränssnitt i Webdoc.

---

## 7. Risks

| Risk | Konsekvens | Åtgärd |
|------|------------|--------|
| **API-begränsning: max 100 bokningar per anrop** | Vid stora datumintervall kan inte all data hämtas i ett enda anrop | Implementera paginering med offset-parameter och iterera tills all data är hämtad |
| **Felaktigt personnummer i filnamn** | Dokument kan laddas upp till fel patient | Validering av personnummer-format före uppladdning; manuell verifiering av filnamn |
| **API-driftstörning** | Uppladdning eller datahämtning avbryts | Felhantering med retry-logik; loggning av misslyckade operationer för manuell uppföljning |
| **Hantering av känsliga personuppgifter** | Personnummer och patientdata hanteras lokalt | Data lagras inte permanent; skript körs på säkra arbetsstationer inom verksamhetens nätverk; GDPR-rutiner följs |
| **Token-utgång under batch-körning** | Pågående batch avbryts om access token löper ut | Token-livslängd kontrolleras och förnyelse sker automatiskt vid behov |

---

## 8. Testing Process

- Integrationen har testats fullständigt i **Webdocs integrationsmiljö** (`api-integration.carasent.net` / `auth-integration.carasent.net`).
- Testningen har omfattat:
  - OAuth2 client credentials-autentisering (inklusive fallback-metoder)
  - Patientuppslag via personnummer (GET /v2/patients)
  - Uppladdning av dokument i olika format (JPG, PNG, PDF) till testpatienter (POST /v1/clinics/{clinicId}/documents)
  - Hämtning av dokumenttyper, kliniker och användare
  - Batch-uppladdning med automatisk personnummer-extraktion från filnamn
- Framtida testning sker i integrationsmiljön före varje ny release eller ändring. Inga ändringar sätts i produktion utan föregående verifiering i testmiljön.

---

## 9. Release Process

- Integrationen består av Python-skript som körs lokalt på säkra arbetsstationer.
- Uppdateringar görs vid behov (nya funktioner eller buggfixar) och testas alltid i integrationsmiljön först.
- Releaser koordineras internt och driftsätts manuellt efter godkänd testning.
- Inga automatiserade CI/CD-pipelines; ändringar versionshanteras och distribueras manuellt till berörda arbetsstationer.

---

## 10. Technical Contact

- **Name:** Miltiadis Triantafyllou
- **Position/title:** CEO
- **Email:** miltiadis@hjartcentrumhalland.se
- **Phone:** 0720233343

---

## 11. Support Contact

- **Email:** info@hjartcentrumhalland.se
- **Name:** Miltiadis Triantafyllou
- **Phone:** 010-300 19 20
