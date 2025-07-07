#!/usr/bin/env python

import glob
import sys, os
import pathlib

ARTIFACT_DIR = pathlib.Path(os.environ["ARTIFACT_DIR"])
IGNORED_FILES = ("reports_index.html", "pull_request.json", "pull_request-comments.json")

def add_entry(file_path):
    print(f"<li><a href='{file_path.relative_to(ARTIFACT_DIR)}'>{file_path.name}</a></li>")

def report_index_to_html(report_index):
    report_dir = report_index.parent

    report_parent = report_dir.parent

    dirname = report_index.relative_to(ARTIFACT_DIR).parent

    def print_header():
        print()
        print(f"<h1><a  style='text-decoration:none; color: inherit' href='{dirname}'>{dirname}</a></h1>")
        print("<ul>")

    def print_separator():
        print("<br>")

    def print_footer():
        print("</ul>")


    first = True
    for glob in ("*.html", "*.json"):
        for report_file in sorted(report_dir.glob(glob)):
            if report_file.name in IGNORED_FILES: continue
            if first:
                print_header()
                first = False

            add_entry(report_file)

        if not first:
            print_separator()

    if not first:
        print_footer()


def main():
    for report_index in sorted(ARTIFACT_DIR.glob('**/reports_index.html')):
        report_index_to_html(pathlib.Path(report_index))

if __name__ == "__main__":
    sys.exit(main())
