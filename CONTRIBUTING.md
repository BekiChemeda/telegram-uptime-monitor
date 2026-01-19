# Contributing to telegram-uptime-monitor

## Project Goal

Build a reliable uptime monitoring system that:
- checks websites and APIs periodically  
- detects outages and recoveries  
- stores history in PostgreSQL  
- sends Telegram notifications  

---

## Development Setup Tasks

### 1. Environment

- [ ] Install PostgreSQL Server  
- [ ] Create local database  
- [ ] Configure .env file  
- [ ] Install Python dependencies  
- [ ] Verify FastAPI startup  

### 2. Database Layer

- [ ] Design SQLAlchemy models  
- [ ] Create Alembic migrations  
- [ ] Implement repositories for  
  - users  
  - monitors  
  - checks  
  - incidents  

### 3. Monitoring Core

- [ ] Implement HTTP checker  
- [ ] Measure response time  
- [ ] Validate status codes  
- [ ] Save check results  
- [ ] Detect state changes  

### 4. Scheduler

- [ ] Configure APScheduler  
- [ ] Load active monitors  
- [ ] Prevent overlapping jobs  
- [ ] Add timeouts  

### 5. Telegram Bot

- [ ] Implement commands  
  - /start  
  - /add  
  - /list  
  - /delete  
  - /stats  
- [ ] Format alert messages  
- [ ] Rate limiting  

### 6. API Layer

- [ ] CRUD endpoints  
- [ ] Input validation  
- [ ] User ownership checks  

### 7. Security

- [ ] URL validation  
- [ ] SSRF protection  
- [ ] logging  
- [ ] error handling  

### 8. Testing

- [ ] unit tests  
- [ ] integration tests  
- [ ] failure simulation  

### 9. Deployment

- [ ] Dockerfile  
- [ ] docker-compose  
- [ ] production config  

---

## How to Contribute

1. Fork repository  
2. Create feature branch  
3. Write tests  
4. Follow commit style  
5. Open pull request  

---

## Coding Rules

- Use async where possible  
- Write type hints  
- Keep functions small  
- No hardcoded secrets  
- Follow FastAPI structure  
