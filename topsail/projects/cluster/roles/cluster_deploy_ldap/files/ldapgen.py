import types
import base64
import os
import sys
import pathlib
import argparse

"""
Reads a property file passed in parameter, and generates base64-encoded
user&passwords lists.
Expected properties:
- user_password # unique password of the users
- adminpassword # password of the admin user

Add the '--verbose' flag to the command line to show the generated content of stderr
"""

def str2base64(mystr):
    return base64.b64encode(mystr.encode("ascii")).decode("ascii")

def encode_users(prefix, nb):
    """prefix="testuser", nb=20:
    "testuser1,testuser2,...,testuser19"
    and returns it in cleartext and base64-encoded
    """

    mystr = ''
    for x in range(nb):
        mystr += prefix + str(x) + ','

    mystr = mystr[:-1] # remove the trailing comma

    return mystr, str2base64(mystr)


def encode_password(password, nb):
    """Generates "password,password...,password" nb times
       and returns it in cleartext and base64-encoded
    """
    mystr = ''
    for x in range(nb):
        mystr += password + ','

    mystr = mystr[:-1] # remove the trailing comma

    return mystr, str2base64(mystr)


def parse_args():
    """
    Simple argument parser.
    """
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('--secret_props')
    parser.add_argument('--admin_user')
    parser.add_argument('--prefix')
    parser.add_argument('--nbusers')
    parser.add_argument('--verbose', action='store_true')
    parser.add_argument('--test', action='store_true')
    cli_args = parser.parse_args()

    if None in (cli_args.prefix, cli_args.nbusers, cli_args.secret_props):
        parser.error("all arguments are mandatory")

    try:
        fname = pathlib.Path(cli_args.secret_props)
    except IndexError:
        print("ERROR: please provide a property file in parameter.")
        sys.exit(1)

    if not fname.exists():
        print(f"ERROR: file '{fname}' doesn't exist...")
        sys.exit(1)

    args = types.SimpleNamespace()
    args.admin_user = cli_args.admin_user
    args.prefix = cli_args.prefix
    args.nbusers = cli_args.nbusers
    args.user_password = None

    args.admin_password = None

    with open(fname) as f:
        for i, line in enumerate(f.readlines()):
            key, found, value = line.strip().partition("=")
            if not found:
                print(f"WARNING: invalid value line {i}, ignoring.")
                continue
            if key not in args.__dict__.keys():
                print(f"WARNING: unexpected key '{key}' line {i}, ignoring.")
                continue
            args.__dict__[key] = value

    if None in args.__dict__.values():
        print("ERROR: not all the properties have been set ...")
        print("INFO: expected properties:", ", ".join(args.__dict__.keys()))
        sys.exit(1)


    args.verbose = cli_args.verbose
    args.test = cli_args.test

    try:
        args.nbusers = int(args.nbusers)
    except ValueError:
        print("ERROR: could not parse the number of users as an integer.")
        sys.exit(1)

    return args

if __name__ == "__main__":
    args = parse_args()

    users, users64 = encode_users(args.prefix, args.nbusers)
    passwords, passwords64 = encode_password(args.user_password, args.nbusers)

    adminuser64 = str2base64(args.admin_user)
    adminpassword64 = str2base64(args.admin_password)

    if args.test:
        print("test mode: all good, exiting.")
        sys.exit(0)

    print(f"""\
export cluster_ldap_adminuser64="{adminuser64}"
export cluster_ldap_adminpassword64="{adminpassword64}"
export cluster_ldap_users64="{users64}"
export cluster_ldap_passwords64="{passwords64}"\

export cluster_ldap_password={args.user_password}
export cluster_ldap_adminuser="{args.admin_user}"
export cluster_ldap_adminpassword="{args.admin_password}"
""")

    if args.verbose:
        print(f"""
users             = {users}
b64(users)        = {users64}
passwords         = {passwords}
b64(passwords)    = {passwords64}
adminuser         = {args.admin_user}
b64(adminuser)    = {adminuser64}
adminpassword     = {args.admin_password}
b64(adminpassord) = {adminpassword64}\
""", file=sys.stderr)
