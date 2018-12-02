Keypirinha Package Control
==========================

This is a package for the fast keystroke launcher keypirinha (http://keypirinha.com/). It provides
commands to install, update and remove third party packages.

## Usage

All commands are prefixed with `PackageControl:`.
* Install Package - Downloads the new package and installs it
* Update Package - Checks if a new version of the package is available and updates if so
* Update All Packages - Does the Update Package command for all installed packages
* Remove Package - Deinstalls the package (configurations are untouched)
* Reinstall Package - Deinstalls the package and installs it again (configurations are untouched)
* Reinstall Untracked - Reinstalls a already installed package, that was not installed through
  PackageControl (untracked package)
* Reinstall All Untracked - Does the  Reinstall Untracked command for all untracked packages
* Update Repository List - Downloads the list of available package again

## Installation

### Directly from Keypirinha

* Open the `Keypirinha: Console`
* Enter the following:
    ```python
    import keypirinha as kp,keypirinha_net as kpn,os;p="PackageControl.keypirinha-package";d=kpn.build_urllib_opener().open("https://github.com/ueffel/Keypirinha-PackageControl/releases/download/0.2.2/"+p);pb=d.read();d.close();f=open(os.path.join(kp.installed_package_dir(),p),"wb");f.write(pb);f.close()
    ```

### Manually

* Download the `PackageControl.keypirinha-package` from the
  [releases](https://github.com/ueffel/Keypirinha-PackageControl/releases/latest)
* Copy the file into `%APPDATA%\Keypirinha\InstalledPackages` (installed mode) or
  `<Keypirinha_Home>\portable\Profile\InstalledPackages` (portable mode)

## Problems

If you have any problems after updating packages, please try to restart Keypirinha and see if the
problems are still there. The reason for some problems can be [Live
Reloading](http://keypirinha.com/api/overview.html?highlight=tricky#reloading) of packages, also
related: [this issue](https://github.com/Keypirinha/Keypirinha/issues/117).

TL;DR: Python's import/unload machinery can sometimes do weird stuff at runtime. Restarting the
python interpreter helps.

## Default Repository

### Overview

The default repository is maintained by myself, it's called "ueffel's Package Repository". An
overview of available packages can be viewed [here](https://ue.spdns.de/packagecontrol/).

### Submit your own package

If you created your own package and want it to be available via PackageControl to other Keypirinha
users you can submit it [here](https://ue.spdns.de/packagecontrol/new_package). The preferred way of
publishing is Github. Your package repository should have the ready-to-use `.keypirinha-package`
file in the release section. The package repository looks for the newest release (not pre-release) 
that has such a file und exposes it.

(If I find the time for it I will clean up and publish the code for the package repository web app
for everyone that wants his own package repository. It's a python wsgi application written with
flask.)
