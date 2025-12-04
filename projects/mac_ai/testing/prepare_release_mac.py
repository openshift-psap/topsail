def get_install_md(kwargs):
    return f"""\
llama.cpp API remoting GPU acceleration for MacOS
=================================================

Prerequisites
-------------

* Make sure that the following dependencies are installed

```
brew tap slp/krunkit
brew install krunkit

brew install podman ramalama molten-vk
```

* Make sure that a libkrun Podman machine exists
```
export CONTAINERS_MACHINE_PROVIDER=libkrun

podman machine ls

# if you don't have a libkrun machine:
podman machine init
```

Setup
-----

* download and extract the tarball and enter its directory
```
curl -Ssf "{kwargs['ci_build_link']}/{kwargs['tarball_path']}" | tar xv
cd "{kwargs['tarball_dir'].name}"
```

* from inside the tarball directory, run this command once to create a copy of krunkit/libkrun that will be allowed to run our virglrenderer/llama.cpp libraries
```
bash ./{kwargs['krunkit_script_file'].name}
```

* run this command to restart the libkrun podman machine with our libraries
```
bash ./{kwargs['machine_script_file'].name}
```

Try it
------

* run ramalama with our custom image.
```
export CONTAINERS_MACHINE_PROVIDER=libkrun
ramalama run --image {kwargs['ramalama_image']} llama3.2
```

"""

def get_troubleshooting_md(kwargs):
    return f"""\
Troubleshooting
===============

Before anything, double check that your `podman` is using the `libkrun` VM provider:
```
> export CONTAINERS_MACHINE_PROVIDER=libkrun
```
and to validate it:
```
> podman machine info -format json | jq -r .Host.VMType
libkrun
```

Without this, `podman` tries to communicate with `vfkit` VMs, which is not supported.

Running without RamaLama
------------------------

```
podman run -it --rm --device /dev/dri "{kwargs['ramalama_image']}" llama-run --verbose --ngl 99 ollama://smollm:135m
```

Reviewing the container logs
----------------------------

When ramalama is launched, check the container logs with this command:
```
podman logs -f $(podman ps --filter label=ai.ramalama -n1  --format="{{{{.ID}}}}")
```

Look for these line to confirm that the API Remoting is active (or look for errors in the first lines of the logs)
```
load_tensors: offloading 28 repeating layers to GPU
load_tensors: offloading output layer to GPU
load_tensors: offloaded 29/29 layers to GPU
load_tensors:   CPU_Mapped model buffer size =   308.23 MiB
load_tensors:        Metal model buffer size =  1918.35 MiB
```

Reviewing the host-side logs
----------------------------

```
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
- the output of this command:
```
system_profiler SPSoftwareDataType SPHardwareDataType
```
"""

def get_benchmarking_md(kwargs):
    return f"""\
Benchmarking
============

* API Remoting Performance
```
ramalama bench --image {kwargs['ramalama_image']} llama3.2 # API Remoting performance
```

* Native Performance
```
brew install llama.cpp
ramalama --nocontainer bench llama3.2 # native Metal performance
```

* Vulkan/Venus Performance
```
ramalama bench llama3.2 # Venus/Vulkan performance
```

If you want to share your performance, please also include:
- the name of the tarball (`{kwargs['tarball_file'].name}`)
- the name of the container image (`{kwargs['ramalama_image']}`)
- the output of this command:
```
system_profiler SPSoftwareDataType SPHardwareDataType
```
"""
