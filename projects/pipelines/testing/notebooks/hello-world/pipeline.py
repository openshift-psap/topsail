import datetime

from kfp import dsl
from kfp import components

@dsl.component(base_image='registry.redhat.io/ubi8/python-39')
def stage1(index: int) -> float:
    import time

    time1 = time.time()
    print(f"Stage 1 running: {time.ctime(time1)}")
    time.sleep(30 * index)

    return time1

@dsl.component(base_image='registry.redhat.io/ubi8/python-39')
def stage2(time1: float) -> float:
    import time

    time2 = time.time()
    print(f"Stage 1 ran at:  {time.ctime(time1)}")
    print(f"Stage 2 running: {time.ctime(time2)}")
    time.sleep(30)

    return time2

@dsl.component(base_image='registry.redhat.io/ubi8/python-39')
def stage3(time2a: float, time2b: float, time2c: float):
    import datetime
    import time

    print(f"Stage 2a ran at: {time.ctime(time2a)}")
    print(f"Stage 2b ran at: {time.ctime(time2b)}")
    print(f"Stage 2c ran at: {time.ctime(time2c)}")
    print(f"Stage 3 running: {time.ctime(time.time())}")
    time.sleep(30)
    print(f"Stage 3 done: {time.ctime(time.time())}")


@dsl.pipeline(
    name='multi-stage-execution-pipeline',
    description='Shows how to create a multi-stage pipeline.'
)
def my_pipeline():
    time1a = stage1(index=1)
    time1a.set_caching_options(False)
    time1b = stage1(index=2)
    time1b.set_caching_options(False)
    time1c = stage1(index=3)
    time1c.set_caching_options(False)

    time2a = stage2(time1=time1a.output)
    time2a.set_caching_options(False)
    time2b = stage2(time1=time1b.output)
    time2b.set_caching_options(False)
    time2c = stage2(time1=time1c.output)
    time2c.set_caching_options(False)

    time3 = stage3(time2a=time2a.output, time2b=time2b.output, time2c=time2c.output)
    time3.set_caching_options(False)

if __name__ == '__main__':
    from kfp.compiler import Compiler
    Compiler().compile(
        pipeline_func=my_pipeline,
        package_path=__file__.replace('.py', '-v2.yaml'))
