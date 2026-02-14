ARG RAMALAMA_VERSION=0.17.0
FROM quay.io/ramalama/cuda:${RAMALAMA_VERSION}

USER 0

ARG BUILD_FLAVOR="default"
ARG MESA_VERSION=25.2.3-101.fc43

ARG LLAMA_CPP_REPO="https://github.com/ggml-org/llama.cpp"
ARG LLAMA_CPP_VERSION="b4735"
ARG LLAMA_CPP_CMAKE_FLAGS="-DGGML_VULKAN=ON  -DGGML_NATIVE=OFF -DGGML_CPU_ARM_ARCH=native"
ARG LLAMA_CPP_CMAKE_BUILD_FLAGS="--parallel 4"

RUN echo "BUILD_FLAVOR: $BUILD_FLAVOR"

# for API Remoting

RUN if [[ "${BUILD_FLAVOR}" == remoting ]]; then \
      dnf update -y && \
      dnf install --quiet -y libdrm && \
      dnf install -y ftp://ftp.icm.edu.pl/vol/rzm5/linux-rocky/9.7/AppStream/x86_64/os/Packages/l/libdrm-devel-2.4.123-2.el9.x86_64.rpm ; \
    fi

RUN dnf install --quiet -y git cmake gcc gcc-c++

# for CUDA
# install from the base image

RUN dnf clean all

# --- LLAMA.CPP --- #

WORKDIR /app/llama.cpp

RUN git clone "${LLAMA_CPP_REPO}" src \
 && git -C src fetch origin ${LLAMA_CPP_VERSION} \
 && git -C src reset --hard FETCH_HEAD

RUN mkdir -p build \
 && echo "Version: ${LLAMA_CPP_VERSION}" > build/build.flags.log \
 && echo "cmake flags: $LLAMA_CPP_CMAKE_FLAGS" >> build/build.flags.log \
 && echo "Build flags: $LLAMA_CPP_CMAKE_BUILD_FLAGS" >> build/build.flags.log \
 && cd src \
 && set -o pipefail \
 && cmake -S . -B ../build ${LLAMA_CPP_CMAKE_FLAGS} -DGGML_VIRTGPU_BACKEND=ON "-DGGML_CUDA=OFF" | tee ../build/build.prepare.log \
 && cmake --build ../build/ ${LLAMA_CPP_CMAKE_BUILD_FLAGS} | tee ../build/build.compile.log
# GGML_CUDA=OFF because it's already in the image

# --- VIRGLRENDERER --- #

WORKDIR /app/virglrenderer

ARG VIRGLRENDERER_ENABLED=n
ARG VIRGLRENDERER_REPO=https://gitlab.freedesktop.org/kpouget/virglrenderer
ARG VIRGLRENDERER_COMMIT=main-linux
ARG VIRGLRENDERER_MESON_FLAGS="-Dapir=true --buildtype=release --prefix=/usr"


RUN if [[ "${VIRGLRENDERER_ENABLED}" == y ]]; then \
 echo -e "[rocky-appstream]\n\
name=Rocky Linux 9 - AppStream\n\
baseurl=https://download.rockylinux.org/pub/rocky/9/AppStream/\$basearch/os/\n\
gpgcheck=1\n\
enabled=1\n\
gpgkey=https://dl.rockylinux.org/pub/rocky/RPM-GPG-KEY-Rocky-9" > /etc/yum.repos.d/rocky-appstream.repo && \
    dnf install -y libepoxy-devel meson python3-yaml && \
    dnf clean all && \
    rm -rf /var/cache/dnf; \
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
