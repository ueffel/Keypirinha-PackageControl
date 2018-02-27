Keypirinha Package Control
==========================

This is a package for the fast keystroke launcher keypirinha
(http://keypirinha.com/). It provides commands to install, update and remove
third party packages.

## Usage

All commands are prefixed with `PackageControl:`.

## Installation

### Directly from Keypirinha

* Open the `Keypirinha: Console`
* Enter the following:
    ```python
    import keypirinha as kp,keypirinha_net as kpn,os;p="PackageControl.keypirinha-package";d=kpn.build_urllib_opener().open("https://github.com/ueffel/Keypirinha-PackageControl/releases/download/0.1/"+p);pb=d.read();d.close();pp=os.path.join(kp.installed_package_dir(), p);f=open(pp, "wb");f.write(pb);f.close()
    ```

### Manually

* Download the `PackageControl.keypirinha-package` from the [releases](https://github.com/ueffel/Keypirinha-PackageControl/releases/latest)
* Copy the file in your %APPDATA%\Keypirinha\InstalledPackages directory (or <Keypirinha_Home>\portable\Profile\InstalledPackages)
