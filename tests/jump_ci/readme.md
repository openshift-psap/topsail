To build the Jump-CI `main` image in the jump host:

```
ssh $JUMP_HOST
git clone https://github.com/openshift-psap/topsail.git
git submodule update --init

cd topsail

podman build -f ./build/Dockerfile --label  preserve=true -t localhost/topsail:main .
```
