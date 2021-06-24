# Mini Mirror
The mini mirror is a mini entitled yum repo mirror, deployed via a `container-compose.yml` file using `podman-compose`

# Instructions
- Install `podman-compose`
- Copy your entitlement file as `entitlement.pem` into this directory
- Run `./run.sh`
- Wait for the sync container to sync all the files into the volume
- Access the mirror at `http://localhost:8080/...`

# Limits
- Doesn't support HTTPS
- Doesn't support client-authentication (publicly accessible)
