# AUR Packaging for xsarena

This directory contains PKGBUILD files for publishing xsarena on the Arch User Repository (AUR).

## Package Types

### Stable Package: xsarena
- Built from tagged releases on GitHub
- Follows semantic versioning
- Updates occur when new releases are published

### VCS Package: xsarena-git
- Built from the latest commit on the main branch
- Always contains the latest features and fixes
- Updates automatically when built

## PKGBUILD Files

- `PKGBUILD` - For the stable package
- `PKGBUILD-git` - For the VCS package

## Testing Locally

To test the build process locally:

```bash
# Install dependencies
sudo pacman -S --needed base-devel git
yay -S python-build python-installer python-wheel python-typer python-pydantic python-aiohttp python-dotenv

# Build and test the package
makepkg -si

# Verify installation
xsarena --help
lmastudio --help
```

## AUR Upload Process

### Stable Package (xsarena)
1. Create the AUR git repo locally:
   ```bash
   git clone ssh://aur@aur.archlinux.org/xsarena.git
   cd xsarena
   ```
2. Copy files:
   ```bash
   cp /path/to/PKGBUILD .
   makepkg --printsrcinfo > .SRCINFO
   ```
3. Commit and push:
   ```bash
   git add PKGBUILD .SRCINFO
   git commit -m "Initial release 0.1.0"
   git push
   ```

### VCS Package (xsarena-git)
1. Create the AUR git repo:
   ```bash
   git clone ssh://aur@aur.archlinux.org/xsarena-git.git
   cd xsarena-git
   ```
2. Copy the -git PKGBUILD:
   ```bash
   cp /path/to/PKGBUILD .
   makepkg --printsrcinfo > .SRCINFO
   ```
3. Commit and push:
   ```bash
   git add PKGBUILD .SRCINFO
   git commit -m "Initial -git package"
   git push
   ```

## Maintenance Workflow

- For each new tagged release:
  - Update pkgver in stable PKGBUILD
  - Run `updpkgsums`
  - Update .SRCINFO
  - Commit and push to AUR

- For the -git package, no manual version bump is needed; the pkgver() function handles it automatically

## Dependencies

Keep depends in sync with pyproject.toml. Standard Arch package names:
- python-typer, python-pydantic, python-aiohttp, python-dotenv
- python-textual (optional) for the TUI
