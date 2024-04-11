from kfp import dsl
from kfp import components

@dsl.component(base_image='quay.io/hukhan/python:alpine3.6')
def cbrt_loop(n:int, x:int) -> int:
    import math, time
    
    i = 0
    end_time = time.time() + n
    while end_time >= time.time():
        math.sqrt(float(x))
        i += 1

    return i

@dsl.component(base_image='quay.io/hukhan/python:alpine3.6')
def print_msg(msg: str):
    """Print a message."""
    print(msg)

@dsl.pipeline(
    name='timed-multistage-workload',
    description='a simple pipeline with multiple stages that have defined runtimes'
)
def timed_multistage_pipeline():
    # 4 pipelines that each have 3 stages. Each should last 2 minutes.
    duration = 2 * 60
    x = 123456789

    h1_s1 = cbrt_loop(n=duration, x=x)
    h2_s1 = cbrt_loop(n=duration, x=x)
    h3_s1 = cbrt_loop(n=duration, x=x)
    h4_s1 = cbrt_loop(n=duration, x=x)

    h1_s2 = cbrt_loop(n=duration, x=h1_s1.output)
    h2_s2 = cbrt_loop(n=duration, x=h2_s1.output)
    h3_s2 = cbrt_loop(n=duration, x=h3_s1.output)
    h4_s2 = cbrt_loop(n=duration, x=h4_s1.output)

    h1_s3 = cbrt_loop(n=duration, x=h1_s2.output)
    h2_s3 = cbrt_loop(n=duration, x=h2_s2.output)
    h3_s3 = cbrt_loop(n=duration, x=h3_s2.output)
    h4_s3 = cbrt_loop(n=duration, x=h4_s2.output)

    h1 = [h1_s1.output, h1_s2.output, h1_s3.output]
    h2 = [h2_s1.output, h2_s2.output, h2_s3.output]
    h3 = [h3_s1.output, h3_s2.output, h3_s3.output]
    h4 = [h4_s1.output, h4_s2.output, h4_s3.output]

    print_msg(msg=f"p1: {h1}\np2: {h2}\np3: {h3}\np4: {h4}")

if __name__ == '__main__':
    from kfp_tekton.compiler import TektonCompiler
    TektonCompiler().compile(timed_multistage_pipeline, __file__.replace('.py', '.yaml'))
