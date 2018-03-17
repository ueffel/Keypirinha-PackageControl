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
    import keypirinha as kp,keypirinha_net as kpn,os;p="PackageControl.keypirinha-package";d=kpn.build_urllib_opener().open("https://github.com/ueffel/Keypirinha-PackageControl/releases/download/0.2/"+p);pb=d.read();d.close();f=open(os.path.join(kp.installed_package_dir(),p),"wb");f.write(pb);f.close()
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
