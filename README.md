# Keypirinha Package Control

This is a package for the fast keystroke launcher keypirinha (<http://keypirinha.com/>). It provides
commands to install, update and remove third party packages.

## Usage

All commands are prefixed with `PackageControl:`.

| command                 | function                                                                                                     |
|-------------------------|--------------------------------------------------------------------------------------------------------------|
| Install Package         | Downloads the new package and installs it                                                                    |
| Update Package          | Checks if a new version of the package is available and updates if so                                        |
| Update All Packages     | Does the Update Package command for all installed packages                                                   |
| Remove Package          | Deinstalls the package (configurations are untouched)                                                        |
| Reinstall Package       | Deinstalls the package and installs it again (configurations are untouched)                                  |
| Reinstall Untracked     | Reinstalls a already installed package, that was not installed<br>through PackageControl (untracked package) |
| Reinstall All Untracked | Does the  Reinstall Untracked command for all untracked packages                                             |
| Update Repository List  | Downloads the list of available package again                                                                |

![Usage](usage.gif)

## Installation

### Directly from Keypirinha

* Open the `Keypirinha: Console` (Shortcut: F2)
* Enter the following:

    ```python
    import keypirinha as kp,keypirinha_net as kpn,os;p="PackageControl.keypirinha-package";d=kpn.build_urllib_opener().open("https://github.com/ueffel/Keypirinha-PackageControl/releases/download/1.0.4/"+p);pb=d.read();d.close();f=open(os.path.join(kp.installed_package_dir(),p),"wb");f.write(pb);f.close()
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
python interpreter (which means restarting Keypirinha) helps.

## Troubleshooting

As multiple users reported problems that PackageControl just shows "Collecting packages"
([#8](https://github.com/ueffel/Keypirinha-PackageControl/issues/8),
[#11](https://github.com/ueffel/Keypirinha-PackageControl/issues/11),
[#16](https://github.com/ueffel/Keypirinha-PackageControl/issues/16)), here are 2 quick solutions to
solve this:

* Install the current version of PackageControl by running the code snippet above (as this
  particular problem is fixed in
  [#11](https://github.com/ueffel/Keypirinha-PackageControl/issues/11)) or
* Locate the corrupt `last.run` file that causes the problem and delete it. In installed mode it
  would be located in
  `c:\Users\<username>\AppData\Local\Keypirinha\Packages\PackageControl\last.run` and in portable
  mode in `<Keypirinha_Home>\portable\Local\Packages\PackageControl\last.run`.  
  After that you should use the `Reinstall Package` item in keypirinha to reinstall PackageControl
  to make absolutly sure you have the latest version.

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
