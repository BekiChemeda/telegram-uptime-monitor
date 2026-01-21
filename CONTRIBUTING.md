# Contributing to telegram-uptime-monitor

## Project Goal

Build a reliable uptime monitoring system that:

- checks websites and APIs periodically  
- detects outages and recoveries  
- stores history in PostgreSQL  
- sends Telegram notifications  

---

## Development Priorities

Current focus: **API routes and core CRUD workflow before scheduler or bot automation.**

---

## Development Setup Tasks

### 1. Environment

- [x] Install PostgreSQL Server  
- [x] Create local database  
- [x] Configure .env file  
- [x] Install Python dependencies  
- [x] Verify FastAPI startup  

---

### 2. API Layer First

Primary goal is to expose complete HTTP routes before background jobs.

- [ ] Create router structure  
  -[x] users  
  -[ ] monitors  
  -[ ] checks  
- [ ] Implement request schemas with Pydantic  
- [ ] Add input validation  
- [ ] Implement ownership verification  
- [ ] Standardize error responses  
- [ ] Add pagination for lists  

#### Required Endpoints

- [x] POST /users/create  
- [x] GET /users/me  

- [x] POST /monitors  
- [x] GET /monitors  
- [x] GET /monitors/{id}  
- [x] PATCH /monitors/{id}  
- [x] DELETE /monitors/{id}  

- [ ] GET /monitors/{id}/checks  
- [ ] GET /monitors/{id}/stats  

---

### 3. Database Layer

Routes depend on stable data access.

- [ ] Finalize SQLAlchemy models  
- [ ] Create Alembic migrations  
- [ ] Implement repository pattern  
  - user repository  
  - monitor repository  
  - check repository  
  - incident repository  
- [ ] Add transactions and session handling  

---

### 4. Monitoring Core

After routes work manually.

- [ ] Implement HTTP checker service  
- [ ] Measure response time  
- [ ] Validate status codes  
- [ ] Save check results  
- [ ] Detect up or down transitions  
- [ ] Create incident records  

---

### 5. Scheduler

- [ ] Configure APScheduler  
- [ ] Load active monitors  
- [ ] Prevent overlapping jobs  
- [ ] Add timeout handling  
- [ ] Retry strategy  

---

### 6. Telegram Bot Integration

- [ ] Connect bot with API layer  
- [ ] Implement commands  
  - /start  
  - /add  
  - /list  
  - /delete  
  - /stats  
- [ ] Format alert messages  
- [ ] Add rate limiting  

---

### 7. Security

- [ ] URL validation  
- [ ] SSRF protection  
- [ ] request timeouts  
- [ ] structured logging  
- [ ] exception handling  

---

### 8. Testing

- [ ] unit tests for routes  
- [ ] repository tests  
- [ ] checker tests  
- [ ] failure simulations  

---

### 9. Deployment

- [ ] Dockerfile  
- [ ] docker-compose  
- [ ] production configuration  
- [ ] health checks  

---

## How to Contribute

1. Fork repository  
2. Create feature branch  
3. Implement routes with tests first  
4. Follow commit style  
5. Open pull request  

---

## Coding Rules

- Build routes before background logic  
- Use async where possible  
- Write type hints  
- Keep functions small  
- No hardcoded secrets  
- Follow FastAPI structure  
- Repositories must be independent of bot  
