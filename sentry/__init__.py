
__version__ = '0.5'
tagline = 'sentry is dns for fun and profit!'

from sentry import counter

stats = counter.Counter()
domain_stats = counter.Counter()

# default log format
LOG_FORMAT = '[%(asctime)s] [%(name)s] %(levelname)s: %(message)s'

