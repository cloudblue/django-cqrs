#  Copyright © 2020 Ingram Micro Inc. All rights reserved.

from setuptools import find_packages, setup


def read_file(name):
    with open(name, 'r') as f:
        content = f.read().rstrip('\n')
    return content


setup(
    name='django-cqrs',
    author='CloudBlue',
    url='http://connect.cloudblue.com',
    description='Django CQRS data synchronisation',
    long_description=read_file('README.md'),
    long_description_content_type='text/markdown',
    license='Apache License, Version 2.0',

    python_requires='>=3.6',
    zip_safe=True,
    packages=find_packages(),
    include_package_data=True,
    install_requires=read_file('requirements/dev.txt').splitlines(),
    tests_require=read_file('requirements/test.txt').splitlines(),
    setup_requires=['setuptools_scm', 'pytest-runner'],
    use_scm_version=True,

    keywords='django cqrs sql mixin amqp',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Framework :: Django :: 1.11',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: Unix',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Topic :: Communications',
        'Topic :: Database',
    ]
)
