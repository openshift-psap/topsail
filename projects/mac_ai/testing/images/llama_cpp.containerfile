FROM quay.io/fedora/fedora:43
USER 0

ARG BUILD_FLAVOR="default"
ARG MESA_VERSION=25.2.3-101.fc43

RUN echo "BUILD_FLAVOR: $BUILD_FLAVOR"

RUN  \
    dnf update -y && \
    dnf install -y --quiet python3-dnf-plugin-versionlock && \
    dnf copr enable -y slp/mesa-libkrun-vulkan && \
    dnf install -y --quiet mesa-vulkan-drivers-${MESA_VERSION} && \
    dnf versionlock add mesa-vulkan-drivers-${MESA_VERSION} && \
    dnf install -y --quiet vulkan-loader-devel vulkan-tools fmt-devel && \
    dnf copr enable -y jeffmaury/shaderc epel-9-aarch64 && \
    dnf install -y --quiet glslc;


# for API Remoting

RUN if [[ "${BUILD_FLAVOR}" == remoting ]]; then \
      dnf update -y && \
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

# --- VIRGLRENDERER --- #

WORKDIR /app/virglrenderer

ARG VIRGLRENDERER_ENABLED=n
ARG VIRGLRENDERER_REPO=https://gitlab.freedesktop.org/kpouget/virglrenderer
ARG VIRGLRENDERER_COMMIT=main-linux
ARG VIRGLRENDERER_MESON_FLAGS="-Dapir=true --buildtype=release --prefix=/usr"

RUN if [[ "${VIRGLRENDERER_ENABLED}" == y ]]; then \
      dnf install --quiet -y libepoxy-devel meson python3-yaml; \
    fi

RUN if [[ "${VIRGLRENDERER_ENABLED}" == y ]]; then \
 git clone "${VIRGLRENDERER_REPO}" src \
 && git -C src fetch origin ${VIRGLRENDERER_COMMIT} \
 && git -C src reset --hard FETCH_HEAD; \
 fi

RUN if [[ "${VIRGLRENDERER_ENABLED}" == y ]]; then \
 mkdir -p build \
 && echo "Version: ${VIRGLRENDERER_COMMIT}" > build/build.flags.log \
 && echo "meson flags: $VIRGLRENDERER_MESON_FLAGS" >> build/build.flags.log \
 && cd src \
 && set -o pipefail \
 && meson setup ./build ${VIRGLRENDERER_MESON_FLAGS} --prefix=/usr | tee ../build/build.prepare.log \
 && ninja -C ./build | tee ../build/build.compile.log \
 && ninja -C ./build install; \
 fi

# install virglrenderer for krun anyway
RUN if [[ "${VIRGLRENDERER_ENABLED}" != y ]]; then \
    dnf install -y virglrenderer; \
  fi

USER 1001

WORKDIR /app/llama.cpp/build/bin
