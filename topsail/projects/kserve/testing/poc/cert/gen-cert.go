// You can edit this code!
// Click here and start typing.

// Offered as a solution for https://unix.stackexchange.com/questions/234324
package main

import (
	"crypto/rand"
	"crypto/rsa"
	"crypto/x509"
	"crypto/x509/pkix"
	"encoding/pem"
	"math/big"
	"time"
	"os"
)

func getCert() *x509.Certificate {
	return &x509.Certificate{
		SerialNumber: genRandomSerial(),
		Subject: pkix.Name{
			CommonName: os.Args[1],
			Organization: []string{"Example Inc."},
			// other subject data can be added here following https://pkg.go.dev/crypto/x509/pkix#Name
		},
		// WARNING - Go Playground always uses Nov 10 2009 as Now - need to run locally for this to be accurate
		NotBefore: time.Now(),
		NotAfter:  time.Now().AddDate(1, 0, 0), // 1 year
		IsCA:      false,
		// ExtKeyUsage:           []x509.ExtKeyUsage{x509.ExtKeyUsageClientAuth, x509.ExtKeyUsageServerAuth},
		// KeyUsage:              x509.KeyUsageDigitalSignature | x509.KeyUsageKeyEncipherment | x509.KeyUsageKeyAgreement,
		BasicConstraintsValid: true,
	}
}

// Recommend running this code locally if you actually want to use this
// - don't trust private keys given to you from the internet :)
func main() {
	// Consider using elliptic curve instead of RSA
	// - (I'm using RSA because question and answers did)
	pKey, err := rsa.GenerateKey(rand.Reader, 2048)
	if err != nil {
		panic(err)
	}
	printKeyPEM(pKey)

	certTemplate := getCert()
	selfSignedBytes, err := x509.CreateCertificate(rand.Reader, certTemplate, certTemplate, &pKey.PublicKey, pKey)
	if err != nil {
		panic(err)
	}

	printCertPEM(selfSignedBytes)
}

// Generally wouldn't want to print a private key
// - consider writing to a file instead when done locally
func printKeyPEM(pKey *rsa.PrivateKey) {
	pemBytes := pem.EncodeToMemory(&pem.Block{
		Type:  "RSA PRIVATE KEY",
		Bytes: x509.MarshalPKCS1PrivateKey(pKey),
	})
	err := os.WriteFile(os.Args[2] + "/wildcard.key", pemBytes, 0644)
	if err != nil {
		panic(err)
	}
	// fmt.Println(string(pemBytes))
}

func printCertPEM(cert []byte) {
	pemBytes := pem.EncodeToMemory(&pem.Block{
		Type:  "CERTIFICATE",
		Bytes: cert,
	})
	err := os.WriteFile(os.Args[2] + "/wildcard.crt", pemBytes, 0644)
	if err != nil {
		panic(err)
	}
	// fmt.Println(string(pemBytes))
}

func genRandomSerial() *big.Int {
	serialBytes := make([]byte, 18)
	rand.Reader.Read(serialBytes)
	return (&big.Int{}).SetBytes(serialBytes)
}
