from kfp import dsl
from kfp import components

# For more info see: https://stackoverflow.com/questions/18036367/leibniz-formula-for-%CF%80-is-this-any-good-python
# (doesn't need to converge well, just want load)
@dsl.component(base_image='registry.redhat.io/ubi8/python-39')
def pi_approx(n:int) -> float:
    import time

    p = 1.0
    den = 3.0
    end_time = time.time() + n
    flip = True
    while end_time >= time.time():
        if flip:
            p += 1.0/(-den)
            flip = False
        else:
            p += 1.0/(den)
            flip = True

        den += 2.0

    return 4.0 * p

# Somewhat silly formula for a circle using two different approximations for pi
@dsl.component(base_image='registry.redhat.io/ubi8/python-39')
def circle_area(pi1: float, pi2: float, r: float) -> float:
    return pi1 * pi2 * r

@dsl.component(base_image='registry.redhat.io/ubi8/python-39')
def print_msg(msg: str):
    """Print a message."""
    print(msg)

@dsl.pipeline(
    name='pi-workload',
    description='a simple CPU load that computes pi'
)
def pi_pipeline():
    # Find two (identical) approximations for pi
    # and use them in a calculation for the area
    # of a circle with radius 5
    pi1 = pi_approx(n=600)
    pi2 = pi_approx(n=600)
    area_of_circle = circle_area(pi1=pi1.output, pi2=pi2.output, r=5.0)
    print_msg(msg=f"area of circle: {area_of_circle.output}")

if __name__ == '__main__':
    from kfp.compiler import Compiler
    Compiler().compile(
        pipeline_func=pi_pipeline,
        package_path=__file__.replace('.py', '-v2.yaml'))
