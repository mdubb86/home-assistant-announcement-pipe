#!/usr/bin/env python3
"""Release script for home-assistant-announcement-pipe."""

import json
import subprocess
import sys

import questionary
import semver

MANIFEST_PATH = "custom_components/announcement_pipe/manifest.json"


def get_current_version():
    with open(MANIFEST_PATH) as f:
        manifest = json.load(f)
    return manifest["version"]


def update_manifest_version(new_version):
    with open(MANIFEST_PATH) as f:
        manifest = json.load(f)
    manifest["version"] = new_version
    with open(MANIFEST_PATH, "w") as f:
        json.dump(manifest, f, indent=2)
        f.write("\n")


def run(cmd, check=True):
    print(f"  $ {cmd}")
    result = subprocess.run(cmd, shell=True, check=False, capture_output=True, text=True)
    if result.returncode != 0 and check:
        print(f"Error: {result.stderr.strip()}")
        sys.exit(result.returncode)
    return result


def check_gh_auth():
    result = subprocess.run(
        "gh auth status",
        shell=True,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print("Error: Not authenticated with GitHub CLI.")
        print("Please run: gh auth login")
        sys.exit(1)


def main():
    check_gh_auth()

    current = get_current_version()
    ver = semver.Version.parse(current)

    options = {
        f"patch ({ver.bump_patch()})": str(ver.bump_patch()),
        f"minor ({ver.bump_minor()})": str(ver.bump_minor()),
        f"major ({ver.bump_major()})": str(ver.bump_major()),
    }

    print(f"\nCurrent version: {current}\n")

    choice = questionary.select(
        "Select version bump:",
        choices=list(options.keys()),
    ).ask()

    if not choice:
        print("Cancelled.")
        sys.exit(1)

    new_version = options[choice]
    tag = f"v{new_version}"

    print(f"\nBumping {current} → {new_version}\n")

    # Update manifest
    update_manifest_version(new_version)
    print(f"✓ Updated {MANIFEST_PATH}")

    # Git operations
    result = run("git diff --name-only")
    if not result.stdout.strip():
        print("No changes to commit.")
        sys.exit(1)

    run(f"git add {MANIFEST_PATH}")
    run(f'git commit -m "release {tag}"')
    print("✓ Committed changes")

    run("git push")
    print("✓ Pushed to origin")

    run(f"git tag {tag}")
    run(f"git push origin {tag}")
    print(f"✓ Created and pushed tag {tag}")

    # Create GitHub release
    run(f'gh release create {tag} --title "{tag}" --generate-notes')
    print(f"✓ Created GitHub release {tag}")

    print(f"\n🎉 Released {tag}!")


if __name__ == "__main__":
    main()
