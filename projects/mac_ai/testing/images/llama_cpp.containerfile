FROM registry.access.redhat.com/ubi9/python-311:9.5-1733172699 AS builder
USER 0
WORKDIR /app

RUN dnf install -y python3-dnf-plugin-versionlock && \
    dnf install -y https://dl.fedoraproject.org/pub/epel/epel-release-latest-9.noarch.rpm && \
    dnf copr enable -y slp/mesa-krunkit epel-9-aarch64 && \
    dnf install -y mesa-vulkan-drivers-24.1.2-101.el9.aarch64 && \
    dnf versionlock  mesa-vulkan-drivers-24.1.2-101.el9.aarch64 && \
    dnf install -y git cmake ninja-build gcc gcc-c++ vulkan-loader-devel vulkan-tools fmt-devel && \
    dnf copr enable -y jeffmaury/shaderc epel-9-aarch64 && \
    dnf install -y glslc && \
    dnf clean all

ENV CMAKE_ARGS="-DGGML_KOMPUTE=1 -DKOMPUTE_OPT_USE_BUILT_IN_FMT=OFF"
ENV FORCE_CMAKE=1

RUN git clone https://github.com/ggml-org/llama.cpp src
RUN mkdir build
RUN git -C src submodule update --init ggml/src/ggml-kompute/kompute
# edit ./ggml/src/ggml-kompute/kompute/CMakeLists.txt to remove Werror
RUN cd src && \
    cmake -S . -B ../build -DGGML_VULKAN=ON  -DGGML_NATIVE=OFF -DGGML_CPU_ARM_ARCH=native && \
    cmake --build ../build/

# Stage 2: Create final image with minimal content
FROM registry.access.redhat.com/ubi9/python-311:9.5-1733172699

COPY --from=builder /app/ /app
COPY --from=builder /usr/bin/vkcube* /usr/bin/
COPY --from=builder /usr/bin/vulkaninfo /usr/bin/vulkaninfo
COPY --from=builder /usr/lib/ /usr/lib/
COPY --from=builder /usr/lib64/ /usr/lib64/
COPY --from=builder /usr/share/vulkan /usr/share/vulkan
COPY --from=builder /usr/include/vulkan /usr/include/vulkan
COPY --from=builder /etc/ /etc/

USER 1001

WORKDIR /app/build/bin
