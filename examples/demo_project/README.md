# CQRS demo project

It's a simple demo project contains 2 services:

- master: source of domain models. Stores models in PostgreSQL.
- replica: service which get models from master by CQRS. Stores replicated models in MySQL and Redis

## Start project:

```
docker compose up -d db_pgsql db_mysql
docker compose run master ./manage.py migrate
docker compose run replica ./manage.py migrate
docker compose up -d
docker compose run master ./manage.py cqrs_sync --cqrs-id=user -f={}
docker compose run master ./manage.py cqrs_sync --cqrs-id=product -f={}
```

It starts master WEB app on [http://127.0.0.1:8000](http://127.0.0.1:8000) and replica on [http://127.0.0.1:8001](http://127.0.0.1:8001)

You can do something with model instances via WEB interface or django shell on master and see how data changes in replica too.


## Domain models:

### User:

The most common and simple way for replication is used for this model.

### ProductType:

This model isn't being synchronized separately, only with related Product.

### Product:

This models uses custom own written serializer and relation optimization.

### Purchase:

This models uses Django REST Framework serializer. Replica service stores this model in redis.


## Monitoring

You can monitor CQRS queue by tools provided by chosen transport backend.

For this demo we use RabbitMQ with management plugin. You can find it on [http://127.0.0.1:15672](http://127.0.0.1:15672) with credentials `rabbitmq / password`.
