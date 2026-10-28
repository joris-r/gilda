# Status

Shows whether the API and the database are reachable.

## GET /api/health

```http
GET /api/health
```

```http
HTTP/1.1 200 OK
Content-Type: application/json

{"api": "ok", "database": "ok"}
```

When the database is unreachable:

```http
HTTP/1.1 503 Service Unavailable
Content-Type: application/json

{"api": "ok", "database": "unreachable"}
```

## Status page

The page at `/` calls `GET /api/health` and shows:

```
Gilda status
API: reachable
Database: reachable
```

When the database is unreachable:

```
Gilda status
API: reachable
Database: unreachable
```

When the API does not answer:

```
Gilda status
API: unreachable
Database: unknown
```

In French:

```
État de Gilda
API : accessible
Base de données : accessible
```
