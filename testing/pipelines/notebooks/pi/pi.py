from kfp import dsl
from kfp import components

# For more info see: https://stackoverflow.com/questions/18036367/leibniz-formula-for-%CF%80-is-this-any-good-python
# (doesn't need to converge well, just want load)
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
def circle_area(pi1:float, pi2:float, r:float) -> float:
    return pi1 * pi2 * r 

def print_msg(msg: str):
    """Print a message."""
    print(msg)


pi_op = components.create_component_from_func(
    pi_approx, base_image='quay.io/hukhan/python:alpine3.6')
circle_op = components.create_component_from_func(
    circle_area, base_image='quay.io/hukhan/python:alpine3.6')
print_op = components.create_component_from_func(
    print_msg, base_image='quay.io/hukhan/python:alpine3.6')


@dsl.pipeline(
    name='pi-workload',
    description='a simple CPU load that computes pi'
)
def pi_pipeline():
    # Find two (identical) approximations for pi
    # and use them in a calculation for the area
    # of a circle with radius 5
    pi1 = pi_op(600)
    pi2 = pi_op(600)
    area_of_circle = circle_op(pi1.output, pi2.output, 5)
    print_op(f"area of circle: {area_of_circle.output}")

if __name__ == '__main__':
    from kfp_tekton.compiler import TektonCompiler
    TektonCompiler().compile(pi_pipeline, __file__.replace('.py', '.yaml'))
