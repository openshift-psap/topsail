import datetime

from kfp import dsl
from kfp import components

@dsl.component(base_image='registry.redhat.io/ubi8/python-39')
def stage1(index: int) -> datetime.datetime:
    import datetime
    import time

    time1 = datetime.datetime.now()
    print(f"Stage 1 running: {time1}")
    time.sleep(30 * index)

    return time1

@dsl.component(base_image='registry.redhat.io/ubi8/python-39')
def stage2(time1: datetime.datetime) -> datetime.datetime:
    import datetime
    import time

    time2 = datetime.datetime.now()
    print(f"Stage 1 ran at:  {time1}")
    print(f"Stage 2 running: {time2}")
    time.sleep(30)

    return time2

@dsl.component(base_image='registry.redhat.io/ubi8/python-39')
def stage3(time2a: datetime.datetime, time2b: datetime.datetime, time2c: datetime.datetime):
    import datetime
    import time

    print(f"Stage 2a ran at: {time2a}")
    print(f"Stage 2b ran at: {time2b}")
    print(f"Stage 2c ran at: {time2c}")
    print(f"Stage 3 running: {datetime.datetime.now()}")
    time.sleep(30)
    print(f"Stage 3 done: {datetime.datetime.now()}")


@dsl.pipeline(
    name='multi-stage-execution-pipeline',
    description='Shows how to create a multi-stage pipeline.'
)
def my_pipeline():
    time1a = stage1(1)
    time1b = stage1(2)
    time1c = stage1(3)

    time2a = stage2(time1a.output)
    time2b = stage2(time1b.output)
    time2c = stage2(time1c.output)

    stage3(time2a.output, time2b.output, time2c.output)

if __name__ == '__main__':
    from kfp.compiler import Compiler
    Compiler().compile(my_pipeline, __file__.replace('.py', '.yaml'))
