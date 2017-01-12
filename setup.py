#!/usr/bin/env python
from setuptools import find_packages, setup

with open('README.md') as readme_file:
    README = readme_file.read()


with open('requirements.txt') as requirements_file:
    install_requires = requirements_file.read().split('\n')


setup(
    name='lambda-deployer',
    version='0.1.0',
    description="Deployer for lambda services",
    long_description=README,
    author="Scott Scoble",
    author_email='scott@scoble.tech',
    url='https://github.com/wscoble/lambda-deployer',
    packages=find_packages(exclude=['tests']),
    install_requires=install_requires,
    license="Apache License 2.0",
    package_data={'deployer': ['*.json']},
    include_package_data=True,
    zip_safe=False,
    keywords='chefit',
    entry_points={
        'console_scripts': [
            'lambda-deployer = deployer.cli:main',
        ]
    },
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Natural Language :: English',
        "Programming Language :: Python :: 2",
        'Programming Language :: Python :: 2.7',
    ],
)
