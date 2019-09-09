Django CQRS
===========

`django-cqrs` is an Django application, that implements CQRS data synchronisation between several Django microservices.


CQRS
----
In Connect we have a rather complex Domain Model. There are many microservices, that are [decomposed by subdomain](https://microservices.io/patterns/decomposition/decompose-by-subdomain.html) and which follow [database-per-service](https://microservices.io/patterns/data/database-per-service.html) pattern. These microservices have rich and consistent APIs. They are deployed in cloud k8s cluster and scale automatically under load. Many of these services aggregate data from other ones and usually [API Composition](https://microservices.io/patterns/data/api-composition.html) is totally enough. But, some services are working too slowly with API JOINS, so another pattern needs to be applied.

The pattern, that solves this issue is called [CQRS - Command Query Responsibility Segregation](https://microservices.io/patterns/data/cqrs.html). Core idea behind this pattern is that view databases (replicas) are defined for efficient querying and DB joins. Applications keep their replicas up to data by subscribing to [Domain events](https://microservices.io/patterns/data/domain-event.html) published by the service that owns the data. Data is [eventually consistent](https://en.wikipedia.org/wiki/Eventual_consistency) and that's okay for non-critical business transactions.


Examples
========

Integration
-----------
* Setup `RabbitMQ`
* Install `django-cqrs`
* Apply changes to master service, according to RabbitMQ settings
```python
# models.py

from django.db import models
from dj_cqrs.mixins import MasterMixin


class Account(MasterMixin, models.Model):
    CQRS_ID = 'account'
    
    
class Author(MasterMixin, models.Model):
    CQRS_ID = 'author'
    CQRS_SERIALIZER = 'app.api.AuthorSerializer'
```

```python
# settings.py

CQRS = {
    'transport': 'dj_cqrs.transport.rabbit_mq.RabbitMQTransport',
    'host': RABBITMQ_HOST,
    'port': RABBITMQ_PORT,
    'username': RABBITMQ_USERNAME,
    'password': RABBITMQ_PASSWORD,
}

```
* Apply changes to replica service, according to RabbitMQ settings
```python
from django.db import models
from dj_cqrs.mixins import ReplicaMixin


class AccountRef(ReplicaMixin, models.Model):
    CQRS_ID = 'account'
    
    id = models.IntegerField(primary_key=True)
    

class AuthorRef(ReplicaMixin, models.Model):
    CQRS_ID = 'author'
    CQRS_CUSTOM_SERIALIZATION = True
    
    @classmethod
    def cqrs_create(cls, **mapped_data):
        # Override here
        pass
        
    def cqrs_update(self, **mapped_data):
        # Override here
        pass
```

```python
# settings.py

CQRS = {
    'transport': 'dj_cqrs.transport.RabbitMQTransport',
    'queue': 'account_replica',
    'host': RABBITMQ_HOST,
    'port': RABBITMQ_PORT,
    'username': RABBITMQ_USERNAME,
    'password': RABBITMQ_PASSWORD,
}
```
* Apply migrations on both services
* Run consumer worker on replica service. Management command: `python manage.py cqrs_consume -w 2`

Notes
-----

When there are master models with related entities in CQRS_SERIALIZER, it's important to have operations within atomic transactions.
CQRS sync will happen on transaction commit. Please, avoid saving master model within transaction more then once to reduce syncing and potential racing on replica side.
Updating of related model won't trigger CQRS automatic synchronization for master model. This needs to be done manually.

Example:
```python
with transaction.atomic():
    publisher = models.Publisher.objects.create(id=1, name='publisher')
    author = models.Author.objects.create(id=1, name='author', publisher=publisher)

with transaction.atomic():
    publisher.name = 'new'
    publisher.save()

    author.save()
```

When only needed instances need to be synchronized, there is a method `is_sync_instance` to set filtering rule. 
It's important to understand, that CQRS counting works even without syncing and rule is applied every time model is updated.

Example:
```python

class FilteredSimplestModel(MasterMixin, models.Model):
    CQRS_ID = 'filter'

    name = models.CharField(max_length=200)

    def is_sync_instance(self):
        return len(str(self.name)) > 2
```


Utilities
---------
Bulk synchronizer without transport (usage example: it may be used for initial configuration). Should be used at planned downtime.
* On master service: `python manage.py cqrs_bulk_dump --cqrs_id=author` -> `author.dump`
* On replica service: `python manage.py cqrs_bulk_load -i=author.dump`

Filter synchronizer over transport (usage example: sync some specific records to a given replica). Can be used dynamically.
* To sync all replicas: `python manage.py cqrs_sync --cqrs_id=author -f={"id__in": [1, 2]}`
* To sync only with one replica: `python manage.py cqrs_sync --cqrs_id=author -f={"id__in": [1, 2]} -q=replica`

Development
===========

1. Python 2.7+
0. Install dependencies `requirements/dev.txt`

Testing
=======

Unit testing
------
1. Python 2.7+
0. Install dependencies `requirements/test.txt`
0. `export PYTHONPATH=/your/path/to/django-cqrs/`

Check code style: `flake8`
Run tests: `pytest`

Tests reports are generated in `tests/reports`. 
* `out.xml` - JUnit test results
* `coverage.xml` - Coverage xml results

To generate HTML coverage reports use:
`--cov-report html:tests/reports/cov_html`


Integrational testing
------
1. docker-compose
0. `cd integration_tests`
0. `docker-compose run master`
