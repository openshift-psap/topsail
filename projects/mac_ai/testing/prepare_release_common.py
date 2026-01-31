def get_release_md(kwargs):
    return f"""\
CI build
--------

* Build system:  `{kwargs['build_system_description']}`
* Build date:    `{kwargs['build_date']}`
* Build version: `{kwargs['build_version']}`

* [INSTALL]({kwargs['ci_build_link']}/{kwargs['tarball_content_path']}/INSTALL.md)
* [BENCHMARKING]({kwargs['ci_build_link']}/{kwargs['tarball_content_path']}/BENCHMARKING.md)
* [TROUBLESHOOTING]({kwargs['ci_build_link']}/{kwargs['tarball_content_path']}/TROUBLESHOOTING.md)
* [tarball]({kwargs['ci_build_link']}/{kwargs['tarball_path']})
* [build logs]({kwargs['ci_build_link']})

Sources
-------

* virglrenderer source: {kwargs['virglrenderer_version_link']}
* llama.cpp source    : {kwargs['llama_cpp_version_link']}
* ramalama source     : {kwargs['ramalama_version_link']}

Ramalama image
--------------
`{kwargs['ramalama_image']}`

Podman Desktop extension
------------------------
`{kwargs['pde_image_fullname']}`

CI performance test
--------

* [release performance test]({kwargs['ci_perf_link'] or '(Not running in a CI environment)'})
"""

def get_benchmarking_md(kwargs):
    return f"""\
Benchmarking
============

* API Remoting Performance
```
ramalama bench  --image {kwargs['ramalama_image']} llama3.2 # API Remoting performance
# add '--oci-runtime krun' on linux to run in the krun VM
```

* Native Performance
```
brew install llama.cpp
# or
dnf install llama.cpp

ramalama --nocontainer bench llama3.2 # native Metal performance
```

* Vulkan/Venus Performance
```
ramalama bench llama3.2 # Venus/Vulkan performance
# add '--oci-runtime krun' on linux to have the VM performance
```

If you want to share your performance, please also include:
Please share:
- the name of the tarball (`{kwargs['tarball_file'].name}`)
- the name of the container image (`{kwargs['ramalama_image']}`)
- the output of this command:
  - MacOS: `system_profiler SPSoftwareDataType SPHardwareDataType`
  - Linux: `uname -a && cat /etc/os-release`
"""
