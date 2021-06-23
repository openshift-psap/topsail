Code for generating files required for TLS client authentication.

# Background
To perform client-authentication on an NGINX instance, it first must be configured to perform regular TLS server-authentication. In our case, we configure TLS using LetsEncrypt with [this openshift-acme fork](https://github.com/omertuc/openshift-acme). The fork fixes some bugs/limitations that have to do with OpenShift passthrough routes (which are [required](https://docs.openshift.com/container-platform/4.7/networking/routes/secured-routes.html#nw-ingress-creating-a-passthrough-route_secured-routes) when you want to perform client-authentication).

In order to mint a client certificate, a CA (certificate and private key) must be created. The CA certificate and private key will be used to sign locally generated client certificates that can then be given to client software (e.g. yum) in order to authenticate against the server.

The client software (e.g. yum) must be given both the client certificate and the client private key corresponding to that certificate in order to authenticate against the server.

# Files 
(Files marked with * are generated and gitignored) 
```bash
.
├── all.sh # A convenience script - Deletes previously generated artifacts, 
│          # generates a CA private key and a corresponding CA certificate, generates a client
│          # private key along with a client CSR (Certificate Signing Request), then uses the
│          # CA files to mint a client certificate out of the client CSR. The resulting client
│          # certificate and client private key are placed in the `client` directory.
│          # The client certificate and key are also concatenated into `generated_client_creds.pem`.
├── ca # A directory containing scripts and files for the CA
│   ├── csr.cnf # an `openssl req` configuration file, with organization name & country details for the CA.
│   ├── gen_ca.sh # A script for generating a CA private key and corresponding certificate.
│   ├─* generated_ca.crt # The generated CA certificate
│   ├─* generated_ca.key # The generated CA private key
│   └── sign.sh # A script that takes a CSR as input, and uses the generated CA files to mint a client certificate.
├── client # A directory containing scripts and files for the client
│   ├── csr.cnf # an `openssl req` configuration file, with organization name & country details for the client.
│   │           # Note that the organization name for the client must be different from the server, otherwise NGINX
│   │           # will consider it "self-signed".
│   ├── gen_client.sh # A script for generating a client private key and corresponding certificate.
│   ├─* generated_client.crt # The generated client certificate
│   ├─* generated_client.csr # The generated client CSR (usually automatically deleted by `all.sh`)
│   └─* generated_client.key # The generated client private key
│   ├─* generated_client_creds.pem # The client key and certificate, concatenated - for convenience. 
│   │                              # This is the file we place in the CI vault
└── delete.sh # A script to delete all generated files
```

To summarize:
- Run `./all.sh` to generate everything (note that this will destroy existing files).
- All the client needs for client-authentication is the `client/generated_client.key` and `client/generated_client.crt`
- All the server needs for authenticating clients is the `ca/generated_ca.crt` file

# yum
Yum repo definitions on the client have to be configured with the 3 following additional lines:

```ini
[...]
...
sslverify=1
sslclientkey=/client-auth/client.key
sslclientcert=/client-auth/client.crt
```

Where `/client-auth/client.key` is the client private key and `/client-auth/client.crt` is the client certificate.

# NGINX
To enable client-authentication, on top of the regular server-authentication, NGINX has to be configured with these 2 additional server config lines: 
```
...
    ssl_verify_client on;
    ssl_client_certificate /client-auth/client_ca.crt;
...
```
Where `/client-auth/client_ca.crt` is the CA certificate we created. Note that NGINX does not need the CA private key, that key is only needed locally to mint client certificates.




