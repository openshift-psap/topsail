import types
import base64
import os
import sys
import pathlib

"""
Reads a property file passed in parameter, and generates base64-encoded
user&passwords lists.
Expected properties:
- prefix        # prefix of the user names
- nbusers       # number of users to generate. The 0-based index will be happended to the prefix
- password      # unique password of the users
- adminuser     # name of the admin user
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
    args = types.SimpleNamespace()
    args.prefix = None
    args.nbusers = None
    args.password = None

    args.adminuser = None
    args.adminpassword = None

    try:
        fname = pathlib.Path(sys.argv[1])
    except IndexError:
        print("ERROR: please provide a property file in parameter.")
        sys.exit(1)

    if not fname.exists():
        print(f"ERROR: file '{fname}' doesn't exist...")
        sys.exit(1)

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


    args.verbose = "--verbose" in sys.argv

    try:
        args.nbusers = int(args.nbusers)
    except ValueError:
        print("ERROR: could not parse the number of users as an integer.")
        sys.exit(1)

    return args

if __name__ == "__main__":
    args = parse_args()

    users, users64 = encode_users(args.prefix, args.nbusers)
    passwords, passwords64 = encode_password(args.password, args.nbusers)

    adminuser64 = str2base64(args.adminuser)
    adminpassword64 = str2base64(args.adminpassword)
    print(f"""\
export rhods_ldap_adminuser="{adminuser64}"
export rhods_ldap_adminpassword="{adminpassword64}"
export rhods_ldap_users="{users64}"
export rhods_ldap_passwords="{passwords64}"
""")

    if args.verbose:
        print(f"""\
users             = {users}
b64(users)        = {users64}
passwords         = {passwords}
b64(passwords)    = {passwords64}
adminuser         = {args.adminuser}
b64(adminuser)    = {adminuser64}
adminpassord      = {args.adminpassword}
b64(adminpassord) = {adminpassword64}
""", file=sys.stderr)
