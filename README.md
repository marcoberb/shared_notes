# SharedNotes - Sistema di Note Condivise

Un'applicazione web moderna per la gestione collaborativa di note, basata su architettura a microservizi con React.js e Python/FastAPI.

## 🚀 Avvio Rapido in Locale

### Prerequisiti

Prima di iniziare, assicurati di avere installato:

- **Docker Desktop** (versione 4.0 o superiore)
- **Docker Compose** (incluso in Docker Desktop)
- **Git** per clonare il repository

### 📋 Guida Step-by-Step

#### 1. Clone del Repository
```bash
git clone https://github.com/marcoberb/shared_notes.git
cd shared_notes
```

#### 2. Generazione Certificati SSL
L'applicazione utilizza HTTPS per la sicurezza. Genera i certificati SSL locali:

```bash
# Crea la cartella per i certificati
mkdir -p certs

# Genera certificato self-signed per localhost
openssl req -x509 -newkey rsa:4096 -keyout certs/localhost.key -out certs/localhost.crt -days 365 -nodes \
  -subj "/O=SharedNotes/CN=localhost"
```

> **Nota:** Se non hai OpenSSL installato:
> - **macOS:** `brew install openssl`
> - **Windows:** Usa Git Bash o WSL
> - **Linux:** Generalmente già installato

#### 3. Avvio dell'Applicazione
```bash
# Verifica che Docker sia in esecuzione
docker --version

# Avvia tutti i servizi
docker-compose -f docker-compose.yml up -d

# Verifica che tutti i container siano attivi
docker-compose ps
```

#### 4. Attesa Inizializzazione
Il primo avvio richiede qualche minuto per:
- Download delle immagini Docker
- Inizializzazione database PostgreSQL
- Setup Keycloak con utenti di test
- Build del frontend React

Monitoraggio dei log:
```bash
# Visualizza i log di tutti i servizi
docker-compose -f docker-compose.yml logs -f

# Log di un servizio specifico
docker-compose -f docker-compose.yml logs -f notes-service
```

#### 5. Accesso all'Applicazione

Una volta completata l'inizializzazione:

- **🌐 Applicazione Frontend:** [https://localhost:3443](https://localhost:3443)
- **🔧 API Gateway:** [http://localhost:8000](http://localhost:8000)
- **🔐 Keycloak Admin:** [http://localhost:8080](http://localhost:8080)
- **📊 API Documentation:** [http://localhost:8000/docs](http://localhost:8000/docs)

## 👥 Utenti di Test

L'applicazione viene inizializzata con utenti predefiniti per facilitare i test:

| Username | Password | Email | Ruolo |
|----------|----------|-------|--------|
| `pippo` | `pippo123` | pippo@example.com | User |
| `pluto` | `pluto123` | pluto@example.com | User |
| `paperino` | `paperino123` | paperino@example.com | User |


## 🏗️ Architettura

```
┌─────────────────┐    ┌──────────────────┐    ┌────────────────────┐
│   React SPA     │────│   API Gateway    │────│   Notes Service    │
│   Frontend      │    │   (FastAPI)      │    │   (FastAPI+DDD)    │
│  localhost:3443 │    │ localhost:8000   │    │ localhost:8002     │
└─────────────────┘    └──────────────────┘    └────────────────────┘
                                │                         │
                                │                         │
                       ┌──────────────────┐               │
                       │    Keycloak      │               │
                       │ (Auth Provider)  │               │
                       │ localhost:8080   │               │
                       └──────────────────┘               │
                                                          │
                                                ┌────────────────────┐
                                                │   PostgreSQL       │
                                                │   Database         │
                                                │ localhost:5432     │
                                                └────────────────────┘
```

## 📖 Funzionalità Implementate

- ✅ **Autenticazione Utente** con Keycloak (OAuth2/OpenID Connect)
- ✅ **Gestione Note** (CRUD completo)
- ✅ **Sistema Tag** per categorizzazione
- ✅ **Condivisione Note** tra utenti
- ✅ **Ricerca Full-Text** integrata in PostgreSQL
- ✅ **Interfaccia Responsive** con React.js
- ✅ **API REST** documentate con OpenAPI/Swagger
- ✅ **Architettura Microservizi** con Domain-Driven Design

## 🔐 Sicurezza

- **HTTPS** obbligatorio per frontend
- **JWT Tokens** per autenticazione API
- **Input Validation** su tutti gli endpoint
- **CORS** configurato per domini autorizzati
- **SQL Injection Prevention** tramite ORM

## 📚 Documentazione

- **API Documentation:** [http://localhost:8000/docs](http://localhost:8000/docs) (Swagger UI)
- **Architettura Completa:** `DOCUMENTAZIONE_PROGETTO.txt`
- **Database Schema:** `database/init/02-init-sharednotes.sql`

## 🤝 Sviluppo

### Struttura del Progetto

```
shared_notes/
├── backend/
│   ├── api-gateway/          # API Gateway FastAPI
│   └── notes-service/        # Microservizio Note (DDD)
├── frontend/                 # React.js SPA
├── database/
│   └── init/                 # Script inizializzazione DB
├── keycloak/                 # Configurazione realm
├── certs/                    # Certificati SSL (generati)
└── docker-compose.yml       # Orchestrazione servizi
```

### Workflow di Sviluppo

1. **Feature Branch:** `git checkout -b feature/nome-feature`
2. **Sviluppo:** Modifica codice con hot-reload attivo
3. **Test:** `docker-compose logs -f` per verificare funzionamento
4. **Commit:** `git commit -m "feat: descrizione feature"`
5. **Push:** `git push origin feature/nome-feature`

## 📊 Monitoring

### Status Endpoint

- `GET /health` - Health check di ogni servizio
- `GET /api/tags` - Test rapido API Notes

### Log Monitoring

```bash
# Logs aggregati
docker-compose logs -f

# Filtra per errori
docker-compose logs | grep ERROR

# Logs specifici per servizio
docker-compose logs -f notes-service
```

## 🚢 Deploy in Produzione

Per il deployment in produzione, consulta la sezione dedicata in `DOCUMENTAZIONE_PROGETTO.txt` che include:

- Configurazione Kubernetes
- Monitoring con Prometheus/Grafana
- CI/CD Pipeline
- Strategie di Backup
- Security Hardening

---

## 📄 Licenza

MIT License - Vedi `LICENSE` per dettagli.

## 📞 Supporto

Per problemi o domande:
1. Controlla la sezione **Troubleshooting** sopra
2. Verifica i logs: `docker-compose -f docker_compose.yml logs -f`
3. Consulta la documentazione completa in `documentazione_progettuale.txt`
