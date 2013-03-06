import time, logging

log = logging.getLogger(__name__)

def howfast(f):
    """ kinda like xruntime but logs the response to logging """
    def decorator(*args, **kwargs ):
        s = time.time()
        resp = f(*args, **kwargs)
        elapsed  = str( int(1000*(time.time() - s)))
        log.debug('call to function %s.%s took %s ms' % (f.__module__, f.func_name, elapsed) )
        return resp
    return decorator
