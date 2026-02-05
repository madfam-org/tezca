# System Management

This directory contains scripts, tools, and documentation for managing the Leyes Como Código platform.

## Quick Reference

### One-Liner Commands (Makefile)

```bash
# Start entire system
make up

# Stop entire system  
make down

# Check system status
make status

# View logs
make logs

# Full cleanup
make clean
```

### System Control Script

```bash
# Start all services
./scripts/system.sh start

# Stop all services
./scripts/system.sh stop

# Restart all services
./scripts/system.sh restart

# Check status
./scripts/system.sh status
```

## Available Management Tools

### Makefile Targets

| Command | Description |
|---------|-------------|
| `make up` | Start all services (Docker + Next.js) |
| `make down` | Stop all services gracefully |
| `make restart` | Restart entire system |
| `make status` | Show status of all running services |
| `make logs` | Stream logs from all containers |
| `make clean` | Clean containers, volumes, caches |
| `make dev` | Start development environment |
| `make build` | Build all Docker images |
| `make test` | Run full test suite with coverage |
| `make ingest` | Run law ingestion pipeline |
| `make viewer` | Open law viewer in browser |
| `make quickstart` | Install deps + start everything |
| `make health` | System health check |

### Individual Scripts

#### Bulk Ingestion
```bash
# Ingest all laws
python scripts/bulk_ingest.py --all --workers 8

# Ingest specific laws
python scripts/bulk_ingest.py --laws amparo,iva,cpeum

# Ingest by priority
python scripts/bulk_ingest.py --priority 1
```

#### Ingestion Status Dashboard
```bash
# View recent ingestion runs
python scripts/ingestion_status.py

# View last 48 hours
python scripts/ingestion_status.py --last 48

# View specific law
python scripts/ingestion_status.py --law ccf
```

#### Platform Testing
```bash
# Run comprehensive platform tests
python scripts/test_platform.py
```

#### XML to JSON Conversion
```bash
# Convert all XML laws to JSON for viewer
python scripts/xml_to_json.py
```

## Service Ports

| Service | Port | URL |
|---------|------|-----|
| Next.js (Viewer) | 3000 | http://localhost:3000 |
| Django API | 8000 | http://localhost:8000 |
| PostgreSQL | 5432 | localhost:5432 |

## System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    User Interface                        │
│  ┌──────────────┐  ┌─────────────┐  ┌───────────────┐  │
│  │ Law Viewer   │  │ Tax Calc    │  │ Search        │  │
│  │ (Next.js)    │  │ (Next.js)   │  │ (Next.js)     │  │
│  └──────────────┘  └─────────────┘  └───────────────┘  │
│         ↓                  ↓                 ↓          │
└─────────┼──────────────────┼─────────────────┼──────────┘
          │                  │                 │
          ↓                  ↓                 ↓
┌─────────────────────────────────────────────────────────┐
│                    Backend Services                      │
│  ┌──────────────┐  ┌─────────────┐  ┌───────────────┐  │
│  │ Django API   │  │ Parsers     │  │ Ingestion     │  │
│  └──────────────┘  └─────────────┘  └───────────────┘  │
└─────────┬──────────────────┬─────────────────┬──────────┘
          │                  │                 │
          ↓                  ↓                 ↓
┌─────────────────────────────────────────────────────────┐
│                      Data Layer                          │
│  ┌──────────────┐  ┌─────────────┐  ┌───────────────┐  │
│  │ PostgreSQL   │  │ XML Files   │  │ JSON Files    │  │
│  └──────────────┘  └─────────────┘  └───────────────┘  │
└──────────────────────────────────────────────────────────┘
```

## Development Workflow

### First Time Setup
```bash
# 1. Clone repository
git clone <repo-url>
cd leyes-como-codigo-mx

# 2. Quick start (installs deps + starts everything)
make quickstart
```

### Daily Development
```bash
# Start your day
make up

# Check everything is running
make status

# During development - view logs
make logs

# Run tests after changes
make test

# End your day
make down
```

### Testing Changes
```bash
# 1. Make your code changes

# 2. Run tests
make test

# 3. Test law ingestion
make ingest

# 4. View results in browser
make viewer
```

## Troubleshooting

### Services Won't Start

```bash
# Check what's using the ports
make status

# Clean everything and restart
make clean
make up
```

### Docker Issues

```bash
# Rebuild images
make build

# Clean and rebuild
make clean
docker-compose build --no-cache
make up
```

### Next.js Won't Start

```bash
# Kill orphaned processes
pkill -f "next dev"

# Clear Next.js cache
rm -rf apps/web/.next
cd apps/web && npm install
make up
```

### Database Issues

```bash
# Access database shell
make db-shell

# Reset database
docker-compose down -v
docker-compose up -d
```

## Logs and Monitoring

### View Logs

```bash
# All services
make logs

# Docker only
docker-compose logs -f

# Specific service
docker-compose logs -f api

# Next.js (if using system.sh)
tail -f logs/nextjs.log
```

### Ingestion Monitoring

```bash
# View dashboard
python scripts/ingestion_status.py

# Check specific law
python scripts/ingestion_status.py --law ccf
```

## Production Deployment

### Pre-deployment Checklist

- [ ] All tests passing (`make test`)
- [ ] All 10 laws ingested successfully
- [ ] Coverage > 85%
- [ ] Docker images built
- [ ] Environment variables configured
- [ ] Database migrations applied

### Deployment Commands

```bash
# Build production images
docker-compose -f docker-compose.prod.yml build

# Start production services
docker-compose -f docker-compose.prod.yml up -d

# Health check
make health
```

## Maintenance

### Regular Maintenance

```bash
# Weekly: Clean up Docker resources
docker system prune -a --volumes

# Monthly: Update dependencies
cd apps/web && npm update
pip install --upgrade -r requirements.txt

# After updates: Rebuild and test
make clean
make build
make test
```

### Backup

```bash
# Backup database
docker-compose exec db pg_dump -U postgres leyes_db > backup.sql

# Backup XML files
tar -czf laws-backup-$(date +%Y%m%d).tar.gz data/federal/

# Backup entire data directory
tar -czf data-backup-$(date +%Y%m%d).tar.gz data/
```

## Support

For issues or questions:
1. Check this documentation
2. View logs: `make logs` or `make status`
3. Run health check: `make health`
4. Check GitHub issues
5. Contact the development team

---

**Last Updated**: 2026-02-02  
**System Version**: Phase B Complete (100%)
