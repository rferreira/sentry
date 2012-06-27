# Licensed to Rackspace, Inc ('Rackspace') under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# Rackspace licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#

import time

from functools import wraps
from collections import defaultdict

DEFAULT_TYPE = 'float'
DEFAULT_GAUGE = 'gauge'


def count_calls(counter=None):
    def wrapper(f):
        @wraps(f)
        def inner(*args, **kwargs):
            if counter:
                counter.add('func_%s' % (f.__name__))
            d = f(*args, **kwargs)
            return d
        return inner
    return wrapper


class Health:
    OK = 1
    WARN = 2
    ERR = 3

Health.to_string = {
    Health.OK: 'ok',
    Health.WARN: 'warn',
    Health.ERR: 'err',
}


class OpsEnum:
    PENDING = 0
    TOTAL = 1


class CounterEnum:
    COUNTER = 0
    SUM = 1
    MIN = 2
    MAX = 3


class Counter(object):

    def __init__(self, time_started=None):
        self._dcount = defaultdict(int)
        self._davg = {}
        self._dops = {}
        self._bound = {}
        self._fvals = {}
        self._health_evaluator = []
        self._health_status = ""
        self._health = Health.OK
        self._dt = {}
        self._time_started = time_started or time.time()
        self._per_sec = {}

    def set_per_sec(self, key):
        """
        Keep track of specific keys per second
        """
        self._per_sec[key] = (None, None)

    def bind(self, key, type, func, *args, **kwargs):
        """
        Bind to a function materialize the args (key -> value), pass in the
        kwargs
        """
        self._bound[key] = (type, func, args, kwargs)

    def change_health_if(self, health_to, health_status, func, *args,
                         **kwargs):
        """
        Bind to a function that changes health
        materialize the args (key -> value), pass in the kwargs
        """
        self._health_evaluator.append((health_to, health_status, func, args,
                                       kwargs))

    def set_type(self, key, type):
        """
        Set the type for the metric
        """
        self._dt[key] = type

    def add(self, key, value=1, type=None):
        self._dcount[key] += value

        if type:
            self._dt[key] = type

    def inc_ops(self, key):
        if key in self._dops:
            val = self._dops[key]
            val[OpsEnum.TOTAL] += 1
            val[OpsEnum.PENDING] += 1
        else:
            self._dops[key] = [1, 1]

    def dec_ops(self, key):
        if key in self._dops:
            val = self._dops[key]
            val[OpsEnum.PENDING] -= 1

    def add_avg(self, key, value, type=None):
        if key in self._davg:
            val = self._davg[key]
            val[CounterEnum.COUNTER] += 1
            val[CounterEnum.SUM] += value

            # Easily extendable
            for en, func in ((CounterEnum.MIN, min), (CounterEnum.MAX, max)):
                val[en] = func(value, val[en])

        else:
            self._davg[key] = [1, value, value, value]

        if type:
            self._dt[key] = type

    def set_health(self, health):
        if health not in (Health.OK, Health.WARN, Health.ERR):
            raise ValueError('Invalid health state: %s' % (health))

        self._health = health

    @property
    def health(self):
        return self._health

    def get_metrics(self, include_uptime=True):
        metrics = []
        m_keys = {}
        for key, stat in self._dcount.iteritems():
            m_keys[key] = stat
            _new_metric = {
                "type": self._dt.get(key, DEFAULT_TYPE),
                "name": key,
                "value": stat,
              }
            metrics.append(_new_metric)

        # Uptime
        if include_uptime:
            val = (time.time() - self._time_started)
            name = "uptime"
            uptime_metric = {
                'type': 'float',
                'name': name,
                'value': val,
            }
            m_keys[name] = val
            metrics.append(uptime_metric)

        for key, stat in self._davg.iteritems():
            count, sumval, minval, maxval = stat
            type = self._dt.get(key, DEFAULT_TYPE)

            if type == "int":
                avgval = int(sumval / count)
            else:
                avgval = sumval / count

            for suffix, val in (("avg", avgval), ("max", maxval),
                                ("min", minval)):
                k = "_".join([key, suffix])
                _new_metric = {
                    "type": type,
                    "name": k,
                    "value": val,
                  }
                m_keys[k] = val
                metrics.append(_new_metric)
        for key, (pen_cnt, total_cnt) in self._dops.iteritems():
            for suffix, type, val in (('pending', 'int', pen_cnt),
                                      ('total', 'gauge', total_cnt)):
                k = "_".join([key, suffix])
                _new_metric = {
                    'type': type,
                    'name': "_".join([key, suffix]),
                    'value': val,
                  }
                m_keys[k] = val
                metrics.append(_new_metric)

        for key, (type, fn, args, kwargs) in self._bound.iteritems():
            vs = []
            for x in args:
                val = m_keys.get(x)
                vs.append(val)

            calc = fn(*vs, **kwargs)
            _new_metric = {
                'name': key,
                'type': type,
                'value': calc
              }
            m_keys[key] = calc
            metrics.append(_new_metric)

        for key, fval in self._fvals.iteritems():
            type = self._dt.get(key, DEFAULT_TYPE)
            _new_metric = {
                'name': key,
                'type': type,
                'value': fval,
              }
            m_keys[key] = fval
            metrics.append(_new_metric)

        for to_health, health_status, fn, args, kwargs in \
            self._health_evaluator:
            vs = []
            for x in args:
                val = m_keys.get(x)
                if val:
                    vs.append(val)

            if fn(*vs, **kwargs):
                self._health = to_health
                self._health_status = health_status

        # Alphabetical
        metrics.sort(key=lambda x: x['name'])
        return metrics

    def per_sec(self):
        """
        called once every X secs.
        Diffs the values versus the previous values, add as a new key
        to a seperate dictionary
        """
        metrics = self.get_metrics()
        for metric in metrics:
            result = self._per_sec.get(metric['name'])
            if result:
                last_val, last_time = result
                if last_time:
                    self._fval[metric['value']] - last_val

    def to_stats(self, include_uptime=True):
        # Get metrics first, evaluate status later
        metrics = self.get_metrics(include_uptime=include_uptime)

        if self._health == Health.OK:
            status = self._health_status or 'service is good'
            state = 'ok'
        elif self._health == Health.WARN:
            status = self._health_status or 'service is warning'
            state = 'warn'
        elif self._health == Health.ERR:
            status = self._health_status or 'service is error'
            state = 'err'
        else:
            status = 'State is unknown, defaulting to error.'
            state = 'err'

        payload = {
            'status': status,
            'state': state,
            'metrics': metrics
        }
        return payload