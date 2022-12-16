Django CQRS
===========
![pyversions](https://img.shields.io/pypi/pyversions/django-cqrs.svg)
[![PyPi Status](https://img.shields.io/pypi/v/django-cqrs.svg)](https://pypi.org/project/django-cqrs/)
[![Docs](https://readthedocs.org/projects/django-cqrs/badge/?version=latest)](https://readthedocs.org/projects/django-cqrs)
[![Coverage](https://sonarcloud.io/api/project_badges/measure?project=django-cqrs&metric=coverage)](https://sonarcloud.io/dashboard?id=django-cqrs)
[![Build Status](https://travis-ci.org/cloudblue/django-cqrs.svg?branch=master)](https://travis-ci.org/cloudblue/django-cqrs)
[![PyPI status](https://img.shields.io/pypi/status/django-cqrs.svg)](https://pypi.python.org/pypi/django-cqrs/)
[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=django-cqrs&metric=alert_status)](https://sonarcloud.io/dashboard?id=django-cqrs)
[![PyPI Downloads](https://img.shields.io/pypi/dm/django-cqrs)](https://pypi.org/project/django-cqrs/)

`django-cqrs` is an Django application, that implements CQRS data synchronisation between several Django microservices.


CQRS
----
In Connect we have a rather complex Domain Model. There are many microservices, that are [decomposed by subdomain](https://microservices.io/patterns/decomposition/decompose-by-subdomain.html) and which follow [database-per-service](https://microservices.io/patterns/data/database-per-service.html) pattern. These microservices have rich and consistent APIs. They are deployed in cloud k8s cluster and scale automatically under load. Many of these services aggregate data from other ones and usually [API Composition](https://microservices.io/patterns/data/api-composition.html) is totally enough. But, some services are working too slowly with API JOINS, so another pattern needs to be applied.

The pattern, that solves this issue is called [CQRS - Command Query Responsibility Segregation](https://microservices.io/patterns/data/cqrs.html). Core idea behind this pattern is that view databases (replicas) are defined for efficient querying and DB joins. Applications keep their replicas up to data by subscribing to [Domain events](https://microservices.io/patterns/data/domain-event.html) published by the service that owns the data. Data is [eventually consistent](https://en.wikipedia.org/wiki/Eventual_consistency) and that's okay for non-critical business transactions.


Documentation
=============

Full documentation is available at [https://django-cqrs.readthedocs.org](https://django-cqrs.readthedocs.org).


Examples
========

You can find an example project [here](examples/demo_project/README.md)

Integration
-----------
* Setup `RabbitMQ`
* Install `django-cqrs`
* Apply changes to master service, according to RabbitMQ settings
```python
# models.py

from django.db import models
from dj_cqrs.mixins import MasterMixin, RawMasterMixin


class Account(MasterMixin, models.Model):
    CQRS_ID = 'account'
    CQRS_PRODUCE = True  # set this to False to prevent sending instances to Transport
    
    
class Author(MasterMixin, models.Model):
    CQRS_ID = 'author'
    CQRS_SERIALIZER = 'app.api.AuthorSerializer'


# For cases of Diamond Multi-inheritance or in case of Proxy Django-models the following approach could be used:
from mptt.models import MPTTModel
from dj_cqrs.metas import MasterMeta

class ComplexInheritanceModel(MPTTModel, RawMasterMixin):
    CQRS_ID = 'diamond'

class BaseModel(RawMasterMixin):
    CQRS_ID = 'base'

class ProxyModel(BaseModel):
    class Meta:
        proxy = True

MasterMeta.register(ComplexInheritanceModel)
MasterMeta.register(BaseModel)
```

```python
# settings.py

CQRS = {
    'transport': 'dj_cqrs.transport.rabbit_mq.RabbitMQTransport',
    'host': RABBITMQ_HOST,
    'port': RABBITMQ_PORT,
    'user': RABBITMQ_USERNAME,
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
    def cqrs_create(cls, sync, mapped_data, previous_data=None, meta=None):
        # Override here
        pass
        
    def cqrs_update(self, sync, mapped_data, previous_data=None, meta=None):
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
    'user': RABBITMQ_USERNAME,
    'password': RABBITMQ_PASSWORD,
}
```
* Apply migrations on both services
* Run consumer worker on replica service. Management command: `python manage.py cqrs_consume -w 2`

Notes
-----

* When there are master models with related entities in CQRS_SERIALIZER, it's important to have operations within atomic transactions. CQRS sync will happen on transaction commit. 
* Please, avoid saving different instances of the same entity within transaction to reduce syncing and potential racing on replica side.
* Updating of related model won't trigger CQRS automatic synchronization for master model. This needs to be done manually.
* By default `update_fields` doesn't trigger CQRS logic, but it can be overridden for the whole application in settings:
```python
settings.CQRS = {
    ...
    'master': {
        'CQRS_AUTO_UPDATE_FIELDS': True,
    },
    ...
}
```
or a special flag can be used in each place, where it's required to trigger CQRS flow:
```python
instance.save(update_fields=['name'], update_cqrs_fields=True)
```
* When only needed instances need to be synchronized, there is a method `is_sync_instance` to set filtering rule. 
It's important to understand, that CQRS counting works even without syncing and rule is applied every time model is updated.

Example:
```python

class FilteredSimplestModel(MasterMixin, models.Model):
    CQRS_ID = 'filter'

    name = models.CharField(max_length=200)

    def is_sync_instance(self):
        return len(str(self.name)) > 2
```

Django Admin
-----------

Add action to synchronize master items from Django Admin page.

```python
from django.db import models
from django.contrib import admin

from dj_cqrs.admin_mixins import CQRSAdminMasterSyncMixin


class AccountAdmin(CQRSAdminMasterSyncMixin, admin.ModelAdmin):
    ...


admin.site.register(models.Account, AccountAdmin)

```

* If necessary, override ```_cqrs_sync_queryset``` from ```CQRSAdminMasterSyncMixin``` to adjust the QuerySet and use it for synchronization.


Utilities
---------
Bulk synchronizer without transport (usage example: it may be used for initial configuration). May be used at planned downtime.
* On master service: `python manage.py cqrs_bulk_dump --cqrs-id=author` -> `author.dump`
* On replica service: `python manage.py cqrs_bulk_load -i=author.dump`

Filter synchronizer over transport (usage example: sync some specific records to a given replica). Can be used dynamically.
* To sync all replicas: `python manage.py cqrs_sync --cqrs-id=author -f={"id__in": [1, 2]}`
* To sync all instances only with one replica: `python manage.py cqrs_sync --cqrs-id=author -f={} -q=replica`

Set of diff synchronization tools:
* To get diff and synchronize master service with replica service in K8S: 
```bash
kubectl exec -i MASTER_CONTAINER -- python manage.py cqrs_diff_master --cqrs-id=author | 
    kubectl exec -i REPLICA_CONTAINER -- python manage.py cqrs_diff_replica |
    kubectl exec -i MASTER_CONTAINER -- python manage.py cqrs_diff_sync
```

* If it's important to check sync and clean up deleted objects within replica service in K8S:
```bash
kubectl exec -i REPLICA_CONTAINER -- python manage.py cqrs_deleted_diff_replica --cqrs-id=author | 
    kubectl exec -i MASTER_CONTAINER -- python manage.py cqrs_deleted_diff_master |
    kubectl exec -i REPLICA_CONTAINER -- python manage.py cqrs_deleted_sync_replica
```

Development
===========

1. Python 3.7 +
2. Install dependencies `requirements/dev.txt`
3. We use `isort` library to order and format our imports, and we check it using `flake8-isort` library (automatically on `flake8` run).  
For convenience you may run `isort .` to order imports.


Testing
=======

Unit testing
------
1. Python 3.7 +
2. Install dependencies `requirements/test.txt`
3. `export PYTHONPATH=/your/path/to/django-cqrs/`

Run tests with various RDBMS:
- `cd integration_tests`
- `DB=postgres docker-compose -f docker-compose.yml -f rdbms.yml run app_test`
- `DB=mysql docker-compose -f docker-compose.yml -f rdbms.yml run app_test`

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
