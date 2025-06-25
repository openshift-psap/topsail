#! /usr/bin/env bash

set -o pipefail
set -o errexit
set -o nounset
set -o errtrace

SCRIPT_DIR=$(cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd)

# for krunkit to load the custom virglrenderer library
export DYLD_LIBRARY_PATH=$SCRIPT_DIR/virglrenderer
echo "# for krunkit to load the custom virglrenderer library"
echo "Setting DYLD_LIBRARY_PATH=$DYLD_LIBRARY_PATH"
echo

# for Virglrendrerer to load the ggml-remotingbackend library
echo "# for Virglrendrerer to load the ggml-remotingbackend library"
export VIRGL_APIR_BACKEND_LIBRARY="$SCRIPT_DIR/llama.cpp/libggml-remotingbackend.dylib"
echo "Setting VIRGL_APIR_BACKEND_LIBRARY=$VIRGL_APIR_BACKEND_LIBRARY"
echo

# for llama.cpp remotingbackend to load the ggml-metal backend
export APIR_LLAMA_CPP_GGML_LIBRARY_PATH="$SCRIPT_DIR/llama.cpp/libggml-metal.dylib"
echo "# for llama.cpp remotingbackend to load the ggml-metal backend"
echo "Setting APIR_LLAMA_CPP_GGML_LIBRARY_PATH=$APIR_LLAMA_CPP_GGML_LIBRARY_PATH"
echo

echo "# for llama.cpp remotingbackend to lookup the ggml-metal entrypoints"
export APIR_LLAMA_CPP_GGML_LIBRARY_REG=ggml_backend_metal_reg
export APIR_LLAMA_CPP_GGML_LIBRARY_INIT=ggml_backend_metal_init
echo "Setting APIR_LLAMA_CPP_GGML_LIBRARY_REG=$APIR_LLAMA_CPP_GGML_LIBRARY_REG"
echo "Setting APIR_LLAMA_CPP_GGML_LIBRARY_INIT=$APIR_LLAMA_CPP_GGML_LIBRARY_INIT"
echo

echo "# to ensure that podman loads libkrun"
export CONTAINERS_MACHINE_PROVIDER=libkrun
echo "Setting CONTAINERS_MACHINE_PROVIDER=$CONTAINERS_MACHINE_PROVIDER"
echo

echo "Restarting podman machine ..."
podman machine stop
podman machine start

echo "All done!"
