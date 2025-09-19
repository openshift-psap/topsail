#! /usr/bin/env bash

set -o pipefail
set -o errexit
set -o nounset
set -o errtrace

err_report() {
    echo "Error on line $1"
}

trap 'err_report $LINENO' ERR

BREW_KRUNKIT_PATH=/opt/homebrew/bin/krunkit
PODMAN_KRUNKIT_PATH=/opt/podman/bin/krunkit
SUPPORTED_MAC_OS_VERSION=15

update_from_brew() {
    # krunkit installed_from brew
    krunkit_path=$1
    if [[ ! -f "$krunkit_path" ]]; then
        echo "ERROR: podman's krunkit not found, cannot proceed. (path: $krunkit_path)"
        exit 1
    fi

    MOLTEN_VK_LIB=/opt/homebrew/lib/libMoltenVK.dylib

    if [[ ! -f "$MOLTEN_VK_LIB" ]]; then
        echo "ERROR: $MOLTEN_VK_LIB does not exist. Please install it with 'brew install molten-vk-krunkit'"
        exit 1
    fi

    libkrun_current_path=$(otool -L "$krunkit_path" | grep libkrun | awk '{print $1;}')
    libvirglrenderer_current_path=$(otool -L "$libkrun_current_path" | grep libvirglrenderer.1.dylib | awk '{print $1;}')

    cd bin
    echo "INFO: copying krunkit and libkrun locally ..."
    cp "$krunkit_path" .
    cp "$libkrun_current_path" ./libkrun-efi.dylib # force the name, to avoid naming it libkrun-efi.1.dylib

    echo "INFO: updading the library references ..."
    # krunkit -> libkrun
    install_name_tool -change "$libkrun_current_path" @executable_path/libkrun-efi.dylib ./krunkit

    # libkrun -> libvirglrenderer
    install_name_tool -change "$libvirglrenderer_current_path" @executable_path/libvirglrenderer.1.dylib ./libkrun-efi.dylib

    # virglrenderer -> libMoltenVK
    install_name_tool -change "/opt/homebrew/opt/molten-vk-krunkit/lib/libMoltenVK.dylib" "/opt/homebrew/lib/libMoltenVK.dylib" ./libvirglrenderer.1.dylib
}

update_from_podman() {
    # krunkit installed from Podman Installer
    krunkit_path=$1
    libkrun_current_path=/opt/podman/lib/libkrun-efi.dylib

    cd bin
    echo "INFO: copying krunkit and libkrun locally ..."
    cp -v "$krunkit_path" "$libkrun_current_path" .

    echo "INFO: updading the krunkit/libkrun library references ..."
    # krunkit -> libkrun
    install_name_tool -change "@rpath/libkrun-efi.dylib" "@executable_path/libkrun-efi.dylib" ./krunkit \
        2>&1 | (grep -v "invalidate the code signature" || true)

    # libkrun -> libvirglrenderer
    install_name_tool -change "@rpath/libvirglrenderer.1.dylib" "@executable_path/libvirglrenderer.1.dylib" ./libkrun-efi.dylib

    # libkrun -> self
    install_name_tool -id $PWD/libkrun-efi.dylib ./libkrun-efi.dylib

    # virglrenderer -> libMoltenVK
    install_name_tool -change "/opt/homebrew/opt/molten-vk-krunkit/lib/libMoltenVK.dylib" "/opt/podman/lib/libMoltenVK.dylib" ./libvirglrenderer.1.dylib

    # virglrenderer -> libepoxy
    install_name_tool -change "/opt/homebrew/opt/libepoxy/lib/libepoxy.0.dylib" "/opt/podman/lib/libepoxy.0.dylib" ./libvirglrenderer.1.dylib
}

update_llama_cpp_libs() {
    echo "INFO: updading the ggml library references ..."

    cd bin
    # libggml-metal -> self
    install_name_tool -id "$PWD/libggml-metal.dylib" ./libggml-metal.dylib

    # libggml-metal -> libggml-base
    install_name_tool -change "@rpath/libggml-base.dylib" "$PWD/libggml-base.dylib" ./libggml-metal.dylib

    # libggml-remotingbackend -> self
    install_name_tool -id "$PWD/libggml-remotingbackend.dylib" ./libggml-remotingbackend.dylib

    # libggml-remotingbackend -> libggml-base
    install_name_tool -change "@rpath/libggml-base.dylib" "$PWD/libggml-base.dylib" ./libggml-remotingbackend.dylib

    # libggml-base ->self
    install_name_tool -id "$PWD/libggml-base.dylib" ./libggml-base.dylib
}

main() {
    if [[ ! -f podman_start_machine.api_remoting.sh ]]; then
        echo "ERROR: podman_start_machine.api_remoting.sh not found in the current directory. Please run this in the llama.cpp API remoting release directory."
        exit 1
    fi

    if ! podman machine info >/dev/null; then
        echo "WARNING: podman not available ..."
        echo
        sleep 2
    fi

    if ! command -v sw_vers >/dev/null 2>&1; then
        echo "WARNING: API Remoting only supported on MacOS. 'sw_vers' command missing ..."

    else
        macos_version_major=$(sw_vers --productVersion | cut -d. -f1)
        if [[ "$macos_version_major" != "$SUPPORTED_MAC_OS_VERSION" ]]; then
            echo "WARNING: this tarball only supports MacOS $SUPPORTED_MAC_OS_VERSION"
            echo
            sleep 2
        fi
    fi

    krunkit_path=$(command -v krunkit 2>/dev/null || true)

    if [[ -z "$krunkit_path" ]]; then
        echo "ERROR: krunkit not available ..."
        echo "Please install it from brew (slp/krunkit) or via PodMan Installer"
        exit 1
    fi

    # just in case they're already there ...
    rm -f bin/krunkit bin/libkrun-efi.dylib

    pushd $PWD
    if [[ "$krunkit_path" == "$BREW_KRUNKIT_PATH" ]]; then
        echo "INFO: krunkit installed from brew ..."
        echo "$krunkit_path"
        update_from_brew "$krunkit_path"
    elif [[ "$krunkit_path" == "$PODMAN_KRUNKIT_PATH" ]]; then
        echo "INFO: krunkit installed from podman ..."
        echo "$krunkit_path"
        update_from_podman "$krunkit_path"
    else
        echo "ERROR: krunkit path ($krunkit_path) not recognized ..."
        echo "Should be installed from brew or PodMan Installer."
        exit 1
    fi

    popd >/dev/null

    if [[ ! -f bin/krunkit ]]; then
        echo "ERROR: ./bin/krunkit hasn't be generated. This isn't expected."
        exit 1
    fi

    if [[ ! -f bin/libkrun-efi.dylib ]]; then
        echo "ERROR: ./bin/libkrun-efi.dylib hasn't be generated. This isn't expected."
        exit 1
    fi

    echo "INFO: Regenerating krunkit and libkrun code signatures ..."
    codesign --force -s - ./bin/krunkit ./bin/libkrun-efi.dylib --entitlements ./entitlement/krunkit.entitlements

    pushd $PWD
    update_llama_cpp_libs
    popd >/dev/null

    # ensure that krunkit loads
    echo "INFO Checking that krunkit loads ..."
    if ! ./bin/krunkit --version; then
        echo "ERROR: ./bin/krunkit not working :/"
        exit 1
    fi

    echo "INFO: All done!"

    echo "INFO: Run 'bash ./podman_start_machine.api_remoting.sh' to restart the PodMan machine with the API Remoting libraries."
}

main
