# CQRS demo

## In this demo we have 2 services:

- master: source of domain models
- replica: service which get models from master by CQRS.


## Start:

```
docker-compose up -d db_pgsql db_mysql redis rabbitmq
docker-compose run master ./manage.py migrate
docker-compose run replica ./manage.py migrate
docker-compose up -d
docker-compose run master ./manage.py cqrs_sync --cqrs-id=user -f={}
docker-compose run master ./manage.py cqrs_sync --cqrs-id=product -f={}
```

It starts master WEB app on `127.0.0.1:8000` and replica on `127.0.0.1:8001`

You can do something with model instances via WEB interface on master and see how it changes in replica too.


## Domain models:

### User:

For syncronization of this model we use the most common way of CQRS workflow

### ProductType:

This model is not synchronized separately, only with related Product

### Product:

This models uses custom own written serializer and relation optimization

### Purchase:

This models uses Django REST Framework serializer and stores instances in application cache (redis)


