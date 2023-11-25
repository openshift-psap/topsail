import time, sys, sched, yaml
import datetime
import subprocess as sp
import numpy as np
import logging

RNG_SEED = np.random.default_rng(123456789)

class Timelines:
    # https://arxiv.org/pdf/1607.05356.pdf
    # scale is 1/lamda, or target time between requests
    @staticmethod
    def poisson(n, rng, scale=1.0, t0=0.0, start=0.0, end=60.0):
        t = t0
        delays = rng.exponential(scale=scale, size=n)
        times = []
        for d in delays:
            t += d
            times.append(t)
        times = np.array(times)
        return times * (end/times.max()) + start

    @staticmethod
    def uniform(n, rng, start=0.0, end=60.0):
        return rng.uniform(low=start, high=end, size=n)

    @staticmethod
    def gamma(n, rng, shape=2.0, start=0.0, end=60.0):
        times = rng.gamma(shape, size=n)
        return times * (end/times.max()) + start

    @staticmethod
    def normal(n, rng, mean=0.0, stddev=0.2, start=0.0, end=60.0):
        times = rng.normal(mean, stddev, n)
        times = times - times.min()
        return times * (end/times.max()) + start

    @staticmethod
    def bimodal(n, rng, mean1=-1.0, mean2=1.0, stddev=0.3, start=0.0, end=60.0):
        times1 = rng.normal(mean1, stddev, round(n/2))
        times2 = rng.normal(mean2, stddev, round(n/2))
        times = np.concatenate((times1, times2))
        times = times - times.min()
        return times * (end/times.max()) + start

dry_run_time = 0.0

def prepare(method, distribution, timespan, instances, rng_seed=RNG_SEED, dry_run=False, verbose_dry_run=True):
    distribution_func = getattr(Timelines, distribution, None)
    if distribution_func is None:
        raise ValueError(f"Invalid distribution name '{distribution}'. "
                         f"Available names: {', '.join([f for f in dir(Timelines) if not f.startswith('_')])}")

    distributed_times = distribution_func(instances, rng_seed, end=timespan)

    def time_monotonic():
        return dry_run_time

    def time_sleep(delay):
        global dry_run_time
        dry_run_time += delay
        if not delay:
            return

        if verbose_dry_run:
            logging.info(f"Wait {delay/60:.2f} minutes")
            logging.info(f"Time elapsed: {dry_run_time/60:.2f} minutes")

    params = (time_monotonic, time_sleep) if dry_run \
        else (time.monotonic, time.sleep)

    scheduler = sched.scheduler(*params)

    for index, delay in enumerate(distributed_times):
        scheduler.enter(delay, 1, method, argument=[index, delay])

    return distributed_times, scheduler
