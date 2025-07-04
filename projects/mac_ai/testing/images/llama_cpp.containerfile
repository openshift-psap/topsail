FROM quay.io/fedora/fedora:42
USER 0

ARG BUILD_FLAVOR="default"
ARG MESA_VERSION=25.0.7-100.fc42

RUN echo "BUILD_FLAVOR: $BUILD_FLAVOR"

RUN if [[ "${BUILD_FLAVOR}" != remoting ]]; then \
    dnf update && \
    dnf install -y --quiet python3-dnf-plugin-versionlock && \
    dnf copr enable -y slp/mesa-libkrun-vulkan && \
    dnf install -y --quiet mesa-vulkan-drivers-${MESA_VERSION} && \
    dnf versionlock add mesa-vulkan-drivers-${MESA_VERSION} && \
    dnf install -y --quiet vulkan-loader-devel vulkan-tools fmt-devel && \
    dnf copr enable -y jeffmaury/shaderc epel-9-aarch64 && \
    dnf install -y --quiet glslc; \
 fi

# for API Remoting

RUN if [[ "${BUILD_FLAVOR}" == remoting ]]; then \
      dnf update && \
      dnf install --quiet -y libdrm-devel; \
    fi

RUN dnf install --quiet -y git cmake gcc gcc-c++ && \
    dnf clean all

# --- LLAMA.CPP --- #

WORKDIR /app/llama.cpp

ARG LLAMA_CPP_REPO="https://github.com/ggml-org/llama.cpp"
ARG LLAMA_CPP_VERSION="b4735"
ARG LLAMA_CPP_CMAKE_FLAGS="-DGGML_VULKAN=ON  -DGGML_NATIVE=OFF -DGGML_CPU_ARM_ARCH=native"
ARG LLAMA_CPP_CMAKE_BUILD_FLAGS="--parallel 4"

RUN git clone "${LLAMA_CPP_REPO}" src \
 && git -C src fetch origin ${LLAMA_CPP_VERSION} \
 && git -C src reset --hard FETCH_HEAD

RUN mkdir -p build \
 && echo "Version: ${LLAMA_CPP_VERSION}" > build/build.flags.log \
 && echo "cmake flags: $LLAMA_CPP_CMAKE_FLAGS" >> build/build.flags.log \
 && echo "Build flags: $LLAMA_CPP_CMAKE_BUILD_FLAGS" >> build/build.flags.log \
 && cd src \
 && set -o pipefail \
 && cmake -S . -B ../build ${LLAMA_CPP_CMAKE_FLAGS} | tee ../build/build.prepare.log \
 && cmake --build ../build/ ${LLAMA_CPP_CMAKE_BUILD_FLAGS} | tee ../build/build.compile.log

USER 1001

WORKDIR /app/llama.cpp/build/bin
