#! /usr/bin/env bash

set -o pipefail
set -o errexit
set -o nounset
set -o errtrace

SCRIPT_DIR=$(cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd)

if [[ ! -f "$SCRIPT_DIR/src_info/ramalama.image-info.txt" ]]; then
    echo "ERROR: ramalam.image-info not found in $SCRIPT_DIR/src_info"
    echo "This is unexpected. Did you move this script from it tarball environment?"
    exit 1
fi

ramalama_image=$(cat "$SCRIPT_DIR/src_info/ramalama.image-info.txt")

if [[ ! -f "$SCRIPT_DIR/bin/krunkit" ]]; then
    echo "ERROR: krunkit not found in $SCRIPT_DIR/bin"
    echo "Did you run 'cd $SCRIPT_DIR; bash ./update_krunkit.sh'"
    exit 1
fi

# for krunkit to load the custom virglrenderer library
export DYLD_LIBRARY_PATH="$SCRIPT_DIR/bin"
echo "# for krunkit to load the custom virglrenderer library"
echo "Setting DYLD_LIBRARY_PATH=$DYLD_LIBRARY_PATH"
echo

# for Virglrendrerer to load the ggml-remotingbackend library
echo "# for Virglrendrerer to load the ggml-remotingbackend library"
export VIRGL_APIR_BACKEND_LIBRARY="$SCRIPT_DIR/bin/libggml-remotingbackend.dylib"
echo "Setting VIRGL_APIR_BACKEND_LIBRARY=$VIRGL_APIR_BACKEND_LIBRARY"
echo

# for llama.cpp remotingbackend to load the ggml-metal backend
export APIR_LLAMA_CPP_GGML_LIBRARY_PATH="$SCRIPT_DIR/bin/libggml-metal.dylib"
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

export CONTAINERS_HELPER_BINARY_DIR="$SCRIPT_DIR/krunkit"

echo "Restarting podman machine ..."
podman machine stop
podman machine start

if [[ -z "$(which ramalama)" ]]; then
    echo "WARNING: ramalama isn't available ..."
fi


cat <<EOF
All done!

Try the API Remoting GPU acceleration with RamaLama:
\$ export CONTAINERS_MACHINE_PROVIDER=$CONTAINERS_MACHINE_PROVIDER
\$ ramalama --image $ramalama_image run llama3.2
EOF
