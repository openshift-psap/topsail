#!/usr/bin/env python3

import glob
import sys
import pathlib

def report_index_to_html(report_index):
    report_dir = report_index.parent

    report_parent = report_dir.parent
    print()
    print(f"<h1>{report_parent}</h1>")
    print("<ul>")
    for report_file in sorted(report_dir.glob("*.html")):
        if report_file.name == "reports_index.html": continue
        print(f"<li><a href='{report_file}'>{report_file.name}</a></li>")

    print("<br>")
    for json_file in sorted(report_dir.glob("*.json")):
        print(f"<li><a href='{json_file}'>{json_file.name}</a></li>")
    print("</ul>")

def main():
    for report_index in sorted(glob.glob('./**/reports_index.html', recursive=True)):
        report_index_to_html(pathlib.Path(report_index))

if __name__ == "__main__":
    sys.exit(main())
