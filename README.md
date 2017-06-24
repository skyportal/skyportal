# Baselayer Template App

This template application shows how to leverage Cesium's BaseLayer to
get a batteries-included web application.  It includes:

- A Tornado-based Python web application that can be customized to your liking
- WebSockets
- JavaScript 6 compilation via Babel, with a Redux & React frontend
- Process management via supervisord
- Proxy configuration via nginx
- Authentication (currently using Google) via Python Social Auth
- Distributed task computation, via `dask` and `distributed`

## Customization guide

1. Clone this repository

To be completed.

## Notes

### Database errors, or "fe_sendauth: no password supplied"

On Debian, in `/etc/postgresql/9.6/main/pg_hba.conf`, insert the
following *before* any line starting with `host`:

```
host skyportal skyportal 127.0.0.1/32 trust
host skyportal_test skyportal 127.0.0.1/32 trust
host skyportal skyportal ::1/128 trust
host skyportal_test skyportal ::1/128 trust
```

(The ::1/128 is what localhost translates to in IPV6.)

Also, ensure that PostgreSQL is running on port 5432, and not 5433
(see `/etc/postgresql/9.6/main/postgresql.conf`).

