from kfp import dsl
from kfp import components

@dsl.component(base_image='registry.redhat.io/ubi8/python-39')
def hash_loop(n:int) -> str:
    import hashlib, time
    hasher = hashlib.sha256()

    hasher.update(bytes(n))

    end_time = time.time() + n
    while end_time >= time.time():
        hasher.update(hasher.digest())

    return hasher.hexdigest()

@dsl.component(base_image='registry.redhat.io/ubi8/python-39')
def print_msg(msg: str):
    """Print a message."""
    print(msg)

@dsl.pipeline(
    name='hash-workload',
    description='a simple CPU load generated via sha256 hashing'
)
def hash_pipeline():   
    # Create 4 hash loop components that run for 10 minutes
    duration = 600
    h1 = hash_loop(duration)
    h2 = hash_loop(duration)
    h3 = hash_loop(duration)
    h4 = hash_loop(duration)

    print_msg(f"{h1.output}\n{h2.output}\n{h3.output}\n{h4.output}")

if __name__ == '__main__':
    from kfp.compiler import Compiler
    Compiler().compile(
        pipeline_func=hash_pipeline,
        package_path=__file__.replace('.py', '-v2.yaml'))
