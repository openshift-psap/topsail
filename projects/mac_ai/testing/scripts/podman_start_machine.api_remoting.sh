#! /usr/bin/env bash

set -o pipefail
set -o errexit
set -o nounset
set -o errtrace

MACHINE_NAME="${1:-}"

SCRIPT_DIR=$(cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd)

export CONTAINERS_MACHINE_PROVIDER=libkrun
echo ""
echo "INFO: # for podman to load krunkit/libkrun and not vfkit"
echo "INFO: Setting CONTAINERS_MACHINE_PROVIDER=$CONTAINERS_MACHINE_PROVIDER"
echo

if ! podman machine info >/dev/null; then
    echo "ERROR: podman not available ..."
    exit 1
fi

if ! podman machine inspect 2>/dev/null >/dev/null; then
    echo "ERROR: podman machine inspect not working. Did you run 'CONTAINERS_MACHINE_PROVIDER=libkrun podman machine init'?"
    exit 1
fi

if [[ ! -f "$SCRIPT_DIR/src_info/ramalama.image-info.txt" ]]; then
    echo "ERROR: ramalam.image-info not found in $SCRIPT_DIR/src_info"
    echo "INFO: This is unexpected. Did you move this script from it tarball environment?"
    exit 1
fi

ramalama_image=$(cat "$SCRIPT_DIR/src_info/ramalama.image-info.txt")

if [[ ! -f "$SCRIPT_DIR/bin/krunkit" ]]; then
    echo "ERROR: krunkit not found in $SCRIPT_DIR/bin"
    echo "Did you run 'cd $SCRIPT_DIR; bash ./update_krunkit.sh'"
    exit 1
fi

# for krunkit to load the custom virglrenderer library
echo ""
export DYLD_LIBRARY_PATH="$SCRIPT_DIR/bin"
echo "INFO: # for krunkit to load the custom virglrenderer library"
echo "INFO: Setting DYLD_LIBRARY_PATH=$DYLD_LIBRARY_PATH"
echo

# for Virglrendrerer to load the ggml-remotingbackend library
echo ""
echo "INFO: # for Virglrendrerer to load the ggml-remotingbackend library"
export VIRGL_APIR_BACKEND_LIBRARY="$SCRIPT_DIR/bin/libggml-remotingbackend.dylib"
echo "INFO: Setting VIRGL_APIR_BACKEND_LIBRARY=$VIRGL_APIR_BACKEND_LIBRARY"
echo

# for llama.cpp remotingbackend to load the ggml-metal backend
echo ""
export APIR_LLAMA_CPP_GGML_LIBRARY_PATH="$SCRIPT_DIR/bin/libggml-metal.dylib"
echo "INFO: # for llama.cpp remotingbackend to load the ggml-metal backend"
echo "INFO: Setting APIR_LLAMA_CPP_GGML_LIBRARY_PATH=$APIR_LLAMA_CPP_GGML_LIBRARY_PATH"
echo

echo ""
echo "INFO: # for llama.cpp remotingbackend to lookup the ggml-metal entrypoints"
export APIR_LLAMA_CPP_GGML_LIBRARY_REG=ggml_backend_metal_reg
export APIR_LLAMA_CPP_GGML_LIBRARY_INIT=ggml_backend_metal_init
echo "INFO: Setting APIR_LLAMA_CPP_GGML_LIBRARY_REG=$APIR_LLAMA_CPP_GGML_LIBRARY_REG"
echo "INFO: Setting APIR_LLAMA_CPP_GGML_LIBRARY_INIT=$APIR_LLAMA_CPP_GGML_LIBRARY_INIT"
echo

export VIRGL_APIR_LOG_TO_FILE=/tmp/apir_virglrenderer.log
export APIR_LLAMA_CPP_LOG_TO_FILE=/tmp/apir_llama_cpp.log
echo ""
echo "INFO: # to store the API Remoting hypervisor logs in a readable location"
echo "INFO: Setting VIRGL_APIR_LOG_TO_FILE=$VIRGL_APIR_LOG_TO_FILE"
echo "INFO: Setting APIR_LLAMA_CPP_LOG_TO_FILE=$APIR_LLAMA_CPP_LOG_TO_FILE"

export CONTAINERS_HELPER_BINARY_DIR="$SCRIPT_DIR/bin/"

echo ""
echo "INFO: Restarting podman machine ..."
# $MACHINE_NAME might be empty, podman doesn't mind and takes the default one
podman machine stop "$MACHINE_NAME"
podman machine start "$MACHINE_NAME" --no-info

echo "INFO: Verifying that krunkit has the API Remoting library ..."
virglrenderer_path=$(lsof -c krunkit | grep "$USER" | grep libvirglrenderer | awk '{print $9;}')
if ! echo "$virglrenderer_path" | grep "$(basename $PWD)" --color; then
    echo "ERROR: wrong library loaded :/ ($virglrenderer_path)"
    exit 1
fi

if [[ -z "$(which ramalama)" ]]; then
    echo "WARNING: ramalama isn't available ..."
    echo "WARNING: Please install a recent version (>= v0.10.0)"
elif ! ramalama version >/dev/null 2>/dev/null; then
    echo "WARNING: ramalama version not working ..."
else
    ramalama_version=$(ramalama version | cut -d" " -f3) # ramalama version 0.10.0

    major=$(echo "$ramalama_version" | cut -d. -f1)
    minor=$(echo "$ramalama_version" | cut -d. -f2)

    if [[ "$major" -ge 1 ]]; then
        echo "UNEXPECTED: RamaLama 1.x ($ramalama_version) not released yet."
    elif [[ "$minor" -ge 10 ]]; then
        echo "INFO: RamaLama v$ramalama_version is recent enough ✔"
    else
        echo "ERROR: RamaLama version $ramalama_version will not work."
    fi
fi

cat <<EOF

INFO: Try the API Remoting GPU acceleration with RamaLama:
\$ export CONTAINERS_MACHINE_PROVIDER=$CONTAINERS_MACHINE_PROVIDER
\$ ramalama --image $ramalama_image run llama3.2

INFO: To stop the virtual machine
\$ export CONTAINERS_MACHINE_PROVIDER=$CONTAINERS_MACHINE_PROVIDER
\$ podman machine stop
\$ podman machine rm # to cleanup its files and disks

INFO: All done!
EOF
