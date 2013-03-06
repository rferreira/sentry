
__version__ = '0.5'
tagline = 'sentry is dns for fun and profit!'

from sentry import counter

stats = counter.Counter()
domain_stats = counter.Counter()

# default log format
LOG_FORMAT = '[%(asctime)s] [%(name)s] %(levelname)s: %(message)s'

import time

def howfast(f):
    """ kinda like xruntime but logs the response to logging """
    def decorator(*args, **kwargs ):
        s = time.time()
        resp = f(*args, **kwargs)
        elapsed  = str( int(1000*(time.time() - s)))
        log.info('call to function %s.%s took %s ms' % (f.__module__, f.func_name, elapsed) )
        return resp
    return decorator
