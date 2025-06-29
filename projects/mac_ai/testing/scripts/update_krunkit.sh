#! /usr/bin/env bash

set -o pipefail
set -o errexit
set -o nounset
set -o errtrace
set -x

if [[ ! -f podman_start_machine.api_remoting.sh ]]; then
    echo "ERROR: podman_start_machine.api_remoting.sh not found in the current directory. Please run this in the llama.cpp API remoting release directory."
    exit 1
fi

cd bin

# just in case they're already there ...
rm -f krunkit libkrun-efi.dylib

krunkit_path=/opt/homebrew/bin/krunkit # the code below does not work with all the krunkit builds, so don't use $(which krunkit)
libkrun_current_path=$(otool -L "$krunkit_path" | grep libkrun | awk '{print $1;}')
libvirglrenderer_current_path=$(otool -L "$libkrun_current_path" | grep libvirglrenderer.1.dylib | awk '{print $1;}')

cp "$krunkit_path" "$libkrun_current_path" .

install_name_tool -change "$libkrun_current_path" @executable_path/libkrun-efi.dylib ./krunkit
install_name_tool -change "$libvirglrenderer_current_path" @executable_path/libvirglrenderer.1.dylib ./libkrun-efi.dylib

codesign --force -s - ./krunkit ./libkrun-efi.dylib --entitlements ../entitlement/krunkit.entitlements

echo "All done!"
