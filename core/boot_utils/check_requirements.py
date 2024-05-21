import os
import sys

from packaging.requirements import InvalidRequirement, Requirement
from packaging.version import Version


def check_requirements():
    "Check Python version and installed libs"

    # Check python version --------------------------------------------------------
    py_version = sys.version_info
    if py_version.major != 3 or py_version.minor < 11:
        print("⚠️ \033[33mAxobot requires Python 3.11 or higher.\033[1m")
        sys.exit(1)

    # Check installed modules -----------------------------------------------------

    core_requirements = _get_requirements_from_file("requirements.txt")
    if not _check_requirements_versions(core_requirements):
        print("\n\n Please run \"pip install -r requirements.txt\"")
        sys.exit(1)

def _get_requirements_from_file(filepath: str):
    "Get a list of requirements from a given requirements.txt file"
    requirements: list[Requirement] = []
    with open(filepath, "r", encoding="utf8") as file:
        for line in file.readlines():
            if not line.strip() or line.startswith("#"):
                continue
            try:
                requirements.append(Requirement(line))
            except InvalidRequirement:
                print(f"⚠️ \033[33mInvalid requirement line in requirements.txt: {line}\033[0m")
    return requirements

def _check_requirements_versions(requirements: list[Requirement]):
    "Check if the requirements are correctly installed"
    # list installed packages
    lst = os.popen('pip list --format=freeze')
    pack_list = lst.read().split("\n")
    # map installed packages to their parsed version
    packages_map: dict[str, Version] = {}
    for pack in pack_list:
        if not pack.strip():
            continue
        pack_name, raw_version = pack.split("==")
        packages_map[pack_name.lower()] = Version(raw_version)
    # check if requirements are installed
    all_satisfied = True
    for req in requirements:
        req_name = req.name.lower()
        if req_name not in packages_map:
            print(f"⚠️ \033[33m{req_name} is not installed.\033[0m")
            all_satisfied = False
            continue
        if not req.specifier.contains(packages_map[req_name]):
            print(f"⚠️ \033[33m{req_name} is not correctly installed.\033[0m")
            print(f"\t\033[33m{req_name} {req.specifier} is required.\033[0m")
            print(f"\t\033[33m{req_name} {packages_map[req_name]} is installed.\033[0m")
            all_satisfied = False
    return all_satisfied
