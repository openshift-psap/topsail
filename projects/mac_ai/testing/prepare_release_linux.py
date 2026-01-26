def get_install_md(kwargs):
    return f"""\
llama.cpp API remoting GPU acceleration for Linux
=================================================

Prerequisites
-------------

* Make sure that the following dependencies are installed

```
dnf install ramalama
# or
pip install ramalama
```

Setup
-----

* download and extract the tarball and enter its directory
```
curl -Ssf "{kwargs['ci_build_link']}/{kwargs['tarball_path']}" | tar xv
cd "{kwargs['tarball_dir'].name}"
```

Try it
------

* run ramalama with our custom image.
```
export LD_LIBRARY_PATH=$PWD/bin
ramalama run --oci-runtime krun --image {kwargs['ramalama_image']} llama3.2
```

"""

def get_troubleshooting_md(kwargs):
    return f"""\
Troubleshooting
===============


Running without RamaLama
------------------------

```
export VIRGL_ROUTE_VENUS_TO_APIR=1
export LD_LIBRARY_PATH=$PWD/bin
podman run --oci-runtime krun -it --rm --device /dev/dri "{kwargs['ramalama_image']}" llama-run --verbose --ngl 99 ollama://smollm:135m
```

Reviewing the container logs
----------------------------

When ramalama is launched, check the container logs with this command:
```
podman logs -f $(podman ps --filter label=ai.ramalama -n1  --format="{{{{.ID}}}}")
```

Look for these line to confirm that the API Remoting is active (or look for errors in the first lines of the logs)
```
# TODO: add the API remoting initialization messages
APIR: log_call_duration: waited 72771ns for the API Remoting handshake host reply...
APIR: log_call_duration: waited 76.78ms for the API Remoting LoadLibrary host reply...

load_tensors: offloading 28 repeating layers to GPU
load_tensors: offloading output layer to GPU
load_tensors: offloaded 29/29 layers to GPU
load_tensors:   CPU_Mapped model buffer size =   308.23 MiB
load_tensors:      Vulkan0 model buffer size =  1918.35 MiB
```

Reviewing the host-side logs
----------------------------

```
# TODO: these files can only be accessed via /proc/(pid of krun)/cwd/tmp
cat /tmp/apir_virglrenderer.log
cat /tmp/apir_llama_cpp.log
```

Reporting an issue
------------------

Open issues in {kwargs['llama_cpp_url']}/issues

Please share:
- the content of the logs mentioned above
- the name of the tarball (`{kwargs['tarball_file'].name}`)
- the name of the container image (`{kwargs['ramalama_image']}`)
"""
