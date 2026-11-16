# Woodshed

A guitar practice planner. See [`docs/plans.md`](docs/plans.md) for the spec.

## Run it

You need only Docker (with Compose).

```sh
git clone https://github.com/salexyun/woodshed.git
cd woodshed
make up    # or, without make: docker compose up --build --wait
```

This builds the image, starts Postgres and the app, runs migrations and waits until both are healthy. Open <http://localhost:8000>. Data lives in the `pgdata` volume, so it survives `docker compose restart` and `docker compose down`. Stop with `docker compose down`; add `-v` to delete the data too.

The app reads `DATABASE_URL` and, optionally, `PORT` (default 8000) from the environment.

`make up` also starts the telemetry stack: the OpenTelemetry Collector, Prometheus, Loki, Tempo and Grafana. Open <http://localhost:3000> for the "Woodshed: practice journey" dashboard. The app exports traces, metrics and logs over OTLP when `OTEL_EXPORTER_OTLP_ENDPOINT` is set (the standard `OTEL_*` variables apply); without it, it logs JSON lines to stderr only.
