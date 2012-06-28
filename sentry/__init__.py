
__version__ = '0.1'
tagline = 'sentry is dns for fun and profit!'

from sentry import counter

stats = counter.Counter()
domain_stats = counter.Counter()