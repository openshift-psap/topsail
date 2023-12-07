CUDAPATH=/usr/local/cuda

# Have this point to an old enough gcc (for nvcc)
GCCPATH=/usr

NVCC=nvcc
CCPATH=${GCCPATH}/bin

CFLAGS ?= -Wno-deprecated-declarations

drv:
	PATH=${PATH}:.:${CCPATH}:${PATH} ${NVCC} -I${CUDAPATH}/include -arch=compute_60 -ptx compare.cu -o compare.ptx
	g++ ${CFLAGS} -O3 -Wno-unused-result -I${CUDAPATH}/include -c gpu_burn-drv.cpp
	g++ ${CFLAGS} -o gpu_burn gpu_burn-drv.o -O3 -lcuda -L${CUDAPATH}/lib64 -L${CUDAPATH}/lib -Wl,-rpath=${CUDAPATH}/lib64 -Wl,-rpath=${CUDAPATH}/lib -lcublas -lcudart -o gpu_burn
