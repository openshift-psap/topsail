from kfp import dsl
from kfp import components

def hash_loop(n:int) -> str:
    import hashlib, time
    hasher = hashlib.sha256()

    hasher.update(bytes(n))
    
    end_time = time.time() + n
    while end_time >= time.time():
        hasher.update(hasher.digest())

    return hasher.hexdigest()


def print_msg(msg: str):
    """Print a message."""
    print(msg)


hash_op = components.create_component_from_func(
    hash_loop, base_image='quay.io/hukhan/python:alpine3.6')
print_op = components.create_component_from_func(
    print_msg, base_image='quay.io/hukhan/python:alpine3.6')


@dsl.pipeline(
    name='hash-workload',
    description='a simple CPU load generated via sha256 hashing'
)
def hash_pipeline():   
    # Create 4 hash loop components that run for 10 minutes
    duration = 600
    h1 = hash_op(duration)
    h2 = hash_op(duration)
    h3 = hash_op(duration)
    h4 = hash_op(duration)

    print_op(f"{h1.output}\n{h2.output}\n{h3.output}\n{h4.output}")

if __name__ == '__main__':
    from kfp_tekton.compiler import TektonCompiler
    TektonCompiler().compile(hash_pipeline, __file__.replace('.py', '.yaml'))
