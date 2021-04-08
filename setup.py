import os
from setuptools import setup
from sentry import __version__ as version
from sentry import tagline

setup(
    name = "sentry",
    version = version,
    author = "Rafael Ferreira",
    author_email = "raf@ophion.org",
    description = (tagline),
    license =  'MIT/X11',
    keywords = "dns server async security",
    url = "https://github.com/rferreira/sentry",
    packages=['sentry'],
    long_description='Sentry is a DNS server/proxy with a smart rules engine that allows you to monitor/control/rewrite request in flight',
    classifiers=[
        'Development Status :: 4 - Beta',
        "Topic :: Utilities",
        'License :: OSI Approved :: Apache Software License'
    ],
    install_requires=['futures==2.1.4','pytest==2.3.5','requests==2.20.0','dnspython==1.11.0', 'prettytable==0.7.2'],
    scripts=['scripts/sentry']
)