FROM registry.access.redhat.com/ubi9/python-311:9.5-1742890420 AS builder
USER 0

RUN dnf install -y python3-dnf-plugin-versionlock && \
    dnf install -y https://dl.fedoraproject.org/pub/epel/epel-release-latest-9.noarch.rpm && \
    dnf copr enable -y slp/mesa-krunkit epel-9-aarch64 && \
    dnf install -y mesa-vulkan-drivers-24.1.2-101.el9.aarch64 && \
    dnf versionlock  mesa-vulkan-drivers-24.1.2-101.el9.aarch64 && \
    dnf install -y git cmake ninja-build gcc gcc-c++ vulkan-loader-devel vulkan-tools fmt-devel && \
    dnf copr enable -y jeffmaury/shaderc epel-9-aarch64 && \
    dnf install -y glslc && \
    dnf clean all

# --- LLAMA.CPP --- #

WORKDIR /app/llama.cpp

ARG LLAMA_CPP_VERSION="b4735"
ARG LLAMA_CPP_CMAKE_FLAGS="-DGGML_VULKAN=ON  -DGGML_NATIVE=OFF -DGGML_CPU_ARM_ARCH=native"
ARG LLAMA_CPP_CMAKE_BUILD_FLAGS="--parallel 4"

RUN git clone https://github.com/ggml-org/llama.cpp src -b ${LLAMA_CPP_VERSION}
RUN mkdir build
RUN git -C src submodule update --init ggml/src/ggml-kompute/kompute

RUN mkdir -p ../build && echo "Build flags: $LLAMA_CPP_CMAKE_FLAGS" > ../build/build.flags.log
RUN cd src && set -o pipefail && \
    cmake -S . -B ../build ${LLAMA_CPP_CMAKE_FLAGS} | tee ../build/build.prepare.log && \
    cmake --build ../build/ ${LLAMA_CPP_CMAKE_BUILD_FLAGS} | tee ../build/build.compile.log

# ---

# Stage 2: Create final image with minimal content
FROM registry.access.redhat.com/ubi9/python-311:9.5-1742890420

COPY --from=builder /app/ /app
COPY --from=builder /usr/bin/vkcube* /usr/bin/
COPY --from=builder /usr/bin/vulkaninfo /usr/bin/vulkaninfo
COPY --from=builder /usr/lib/ /usr/lib/
COPY --from=builder /usr/lib64/ /usr/lib64/
COPY --from=builder /usr/share/vulkan /usr/share/vulkan
COPY --from=builder /usr/include/vulkan /usr/include/vulkan
COPY --from=builder /etc/ /etc/

USER 1001

WORKDIR /app/llama.cpp/build/bin
