Django CQRS
===========

`django-cqrs` is an Django application, that implements CQRS data synchronisation between several Django microservices.


CQRS
----
In Connect we have a rather complex Domain Model. There are many microservices, that are [decomposed by subdomain](https://microservices.io/patterns/decomposition/decompose-by-subdomain.html) and which follow [database-per-service](https://microservices.io/patterns/data/database-per-service.html) pattern. These microservices have rich and consistent APIs. They are deployed in cloud k8s cluster and scale automatically under load. Many of these services aggregate data from other ones and usually [API Composition](https://microservices.io/patterns/data/api-composition.html) is totally enough. But, some services are working too slowly with API JOINS, so another pattern needs to be applied.

The pattern, that solves this issue is called [CQRS - Command Query Responsibility Segregation](https://microservices.io/patterns/data/cqrs.html). Core idea behind this pattern is that view databases (replicas) are defined for efficient querying and DB joins. Applications keep their replicas up to data by subscribing to [Domain events](https://microservices.io/patterns/data/domain-event.html) published by the service that owns the data. Data is [eventually consistent](https://en.wikipedia.org/wiki/Eventual_consistency) and that's okay for non-critical business transactions.


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
0. `cd integrational_tests`
0. `docker-compose up`
