package main

import (
	"encoding/base64"
	"fmt"
	"golang.org/x/crypto/bcrypt"
	"os"
)

func main() {
	if len(os.Args) != 2 {
		fmt.Fprintf(os.Stderr, "usage: %s <password>\n", os.Args[0])
        os.Exit(1)
	}

	password := os.Args[1]
    password_hash, err := bcrypt.GenerateFromPassword([]byte(password), bcrypt.DefaultCost)
	if err != nil {
		fmt.Fprintf(os.Stderr, "error: %v\n", err)
        os.Exit(1)
	}
	password_hash_b64 := base64.StdEncoding.EncodeToString(password_hash)
	fmt.Printf("%s", password_hash_b64)
}
