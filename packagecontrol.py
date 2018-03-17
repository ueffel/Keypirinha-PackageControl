from .lib.package import Package
from .lib.RedirectorHandler import RedirectorHandler
import keypirinha as kp
import keypirinha_net as kpn
import os
import configparser
import json
import datetime
import re
import time
import traceback
import urllib

PACKAGE_COMMAND = kp.ItemCategory.USER_BASE + 1


class PackageControl(kp.Plugin):
    """
        Package that provides a means to install, update and remove keypirinha packages
    """
    DEFAULT_REPO = "http://ueffel.bplaced.de/uni/packages.json"
    DEFAULT_AUTOUPDATE = True
    DEFAULT_UPDATE_INTERVAL = 12

    def __init__(self):
        super().__init__()
        self._installed_packages = []
        self._untracked_packages = []
        self._available_packages = []
        self._repo_url = self.DEFAULT_REPO
        self._autoupdate = self.DEFAULT_AUTOUPDATE
        self._update_interval = self.DEFAULT_UPDATE_INTERVAL
        self._urlopener = kpn.build_urllib_opener(extra_handlers=[RedirectorHandler()])
        self.__command_executing = False
        self.__list_updating = False
        self._debug = False

    def on_events(self, flags):
        """
            Reloads the config when its changed and installs missing packages
            Also rebuild the urlopener if network settings are changed
        """
        if flags & kp.Events.PACKCONFIG:
            self._read_config()
            self._check_installed()

        if flags & kp.Events.NETOPTIONS:
            self.dbg("Network settings changed: rebuilding urlopener")
            self._urlopener = kpn.build_urllib_opener()

    def on_start(self):
        """
            Reads config, checks packages and installs missing packages
        """
        self.dbg("Packages root path: {}".format(self._get_packages_root()))
        self._read_config()

        # Adding PackageControl itself, so updating is possible
        if os.path.dirname(__file__).endswith("PackageControl.keypirinha-package") \
                and os.path.dirname(os.path.dirname(__file__)) \
                and "PackageControl" not in self._installed_packages:
            self._installed_packages.append("Keypirinha-PackageControl")

        self._check_installed()

    def on_catalog(self):
        """
            Adds the commands to the catalog
        """
        catalog = []

        install_cmd = self.create_item(
            category=PACKAGE_COMMAND,
            label="PackageControl: Install Package",
            short_desc="Installs a new packages from the repositiory",
            target="install",
            args_hint=kp.ItemArgsHint.REQUIRED,
            hit_hint=kp.ItemHitHint.NOARGS
        )
        catalog.append(install_cmd)

        uninstall_cmd = self.create_item(
            category=PACKAGE_COMMAND,
            label="PackageControl: Remove Package",
            short_desc="Removes already installed packages",
            target="remove",
            args_hint=kp.ItemArgsHint.REQUIRED,
            hit_hint=kp.ItemHitHint.NOARGS
        )
        catalog.append(uninstall_cmd)

        update_cmd = self.create_item(
            category=PACKAGE_COMMAND,
            label="PackageControl: Update Package",
            short_desc="Updates already installed packages to the latest version",
            target="update",
            args_hint=kp.ItemArgsHint.REQUIRED,
            hit_hint=kp.ItemHitHint.NOARGS
        )
        catalog.append(update_cmd)

        reinstall_cmd = self.create_item(
            category=PACKAGE_COMMAND,
            label="PackageControl: Reinstall Package",
            short_desc="Removes packages and installs them again from the repository",
            target="reinstall",
            args_hint=kp.ItemArgsHint.REQUIRED,
            hit_hint=kp.ItemHitHint.NOARGS
        )
        catalog.append(reinstall_cmd)

        reinstall_untracked_cmd = self.create_item(
            category=PACKAGE_COMMAND,
            label="PackageControl: Reinstall untracked package from repository",
            short_desc="Reinstalls a package that was not installed through PackageControl from the repository",
            target="reinstall_untracked",
            args_hint=kp.ItemArgsHint.REQUIRED,
            hit_hint=kp.ItemHitHint.NOARGS
        )
        catalog.append(reinstall_untracked_cmd)

        update_repo_cmd = self.create_item(
            category=PACKAGE_COMMAND,
            label="PackageControl: Update Repository List",
            short_desc="Updates the list of packages from the repository",
            target="update_repo",
            args_hint=kp.ItemArgsHint.FORBIDDEN,
            hit_hint=kp.ItemHitHint.NOARGS
        )
        catalog.append(update_repo_cmd)

        update_all_cmd = self.create_item(
            category=PACKAGE_COMMAND,
            label="PackageControl: Update All Packages",
            short_desc="Updates all currently installed packages to the latest version from the repository",
            target="update_all",
            args_hint=kp.ItemArgsHint.FORBIDDEN,
            hit_hint=kp.ItemHitHint.NOARGS
        )
        catalog.append(update_all_cmd)

        reinstall_all_untracked_cmd = self.create_item(
            category=PACKAGE_COMMAND,
            label="PackageControl: Reinstalls all untracked package from repository",
            short_desc="Reinstalls all packages that were not installed through PackageControl from the repository",
            target="reinstall_all_untracked",
            args_hint=kp.ItemArgsHint.FORBIDDEN,
            hit_hint=kp.ItemHitHint.NOARGS
        )
        catalog.append(reinstall_all_untracked_cmd)

        self.set_catalog(catalog)

    def on_suggest(self, user_input, items_chain):
        """
            Suggests a list of packages for the command
        """
        if not items_chain:
            return

        suggestions = []
        packages = []

        if self.__command_executing:
            self.set_suggestions([self.create_error_item(
                label="Please wait...",
                short_desc="Another command is executing, waiting until it is finished"
            )])
            while self.__command_executing:
                time.sleep(.200)

        self.set_suggestions([self.create_error_item(
            label="Please wait...",
            short_desc="Collecting packages"
        )])

        if items_chain[0].target() == "install":
            self.dbg("Suggesting packages to install")
            packages = [package for package in self._get_available_packages()
                        if package.name not in self._installed_packages]
        elif items_chain[0].target() == "remove" or items_chain[0].target() == "update" \
                or items_chain[0].target() == "reinstall":
            self.dbg("Suggesting packages to update/remove/reinstall")
            packages = [package for package in self._get_available_packages()
                        if package.name in self._installed_packages]
        elif items_chain[0].target() == "reinstall_untracked":
            self.dbg("Suggesting packages to reinstall untracked")
            packages = [package for package in self._get_available_packages()
                        if package.filename in self._untracked_packages]

        for package in packages:
            package_item = items_chain[0].clone()
            package_item.set_short_desc(package.description if package.description else "no description")
            package_item.set_args(package.name)
            suggestions.append(package_item)

        self.set_suggestions(suggestions)

    def on_execute(self, item, action):
        """
            Executes the command
        """
        self.dbg("on_execute() item: {}, action: {}".format(item, action))
        self.dbg("args: {}".format(item.raw_args()))

        if self.__command_executing:
            self.warn("Another command is already executing, doing nothing")
            return

        try:
            self.__command_executing = True
            if item.target() == "install":
                self._install_package(self._get_package(item.raw_args()))
            elif item.target() == "remove":
                self._remove_package(self._get_package(item.raw_args()))
            elif item.target() == "update":
                self._update_package(self._get_package(item.raw_args()))
            elif item.target() == "reinstall":
                package = self._get_package(item.raw_args())
                self._remove_package(package, save_settings=False)
                self._install_package(package)
            elif item.target() == "reinstall_untracked":
                self._install_package(self._get_package(item.raw_args()), force=True)
            elif item.target() == "update_repo":
                self._get_available_packages(True)
                self._check_installed()
            elif item.target() == "update_all":
                self._get_available_packages(True)
                for package_name in self._installed_packages:
                    package = self._get_package(package_name)
                    self._update_package(package)
                self.info("Updating all packages finished")
            elif item.target() == "reinstall_all_untracked":
                for untracked in self._untracked_packages:
                    package = self._get_package_from_filename(untracked)
                    if package:
                        self._install_package(package, force=True, save_settings=False)
                    else:
                        self.info("Package '{}' not found in the repository".format(untracked))
                self._save_settings()
                self.info("Reinstalling all untracked packages finished")
        except Exception as exc:
            self.err("Error occurred while executing command '{}': {}".format(item, exc))
        finally:
            self.__command_executing = False

    def _read_config(self):
        """
            Reads the repo url and the installed packages list from the config
        """
        self.dbg("Reading config")
        settings = self.load_settings()

        self._repo_url = settings.get("repository", "main", self.DEFAULT_REPO)
        self.dbg("repo_url: {}".format(self._repo_url))

        self._installed_packages = list(set(settings.get_multiline("installed_packages", "main")))
        self.dbg("installed_packages: {}".format(self._installed_packages))

        self._autoupdate = settings.get_bool("autoupdate", "main", self.DEFAULT_AUTOUPDATE)
        self.dbg("autoupdate: {}".format(self._autoupdate))

        self._update_interval = settings.get_float("update_interval", "main", self.DEFAULT_UPDATE_INTERVAL)
        self.dbg("update_interval: {}".format(self._update_interval))

    def _save_settings(self):
        """
            Save the user config file with all installed packages
        """
        self.dbg("Saving settings")

        save_path = os.path.join(kp.user_config_dir(), "{}.ini".format(self.package_full_name()))
        config = configparser.ConfigParser()
        config.read(save_path)

        if "main" not in config:
            config.add_section("main")

        config["main"]["repository"] = self._repo_url
        config["main"]["installed_packages"] = "\n{}".format("\n".join(self._installed_packages))

        with open(save_path, "w") as ini_file:
            config.write(ini_file)

    def _check_installed(self):
        """
            Check if installed packages from the config are really present
            Also makes a list of packages that are installed but not in the config (untracked)
        """
        self.dbg("Checking installed packages")

        installed_fs = [file for file in os.listdir(self._get_packages_root())
                        if os.path.isfile(os.path.join(self._get_packages_root(), file))
                        and file.endswith(".keypirinha-package")]

        self.dbg("Filesystem packages: {}".format(installed_fs))

        for installed_package in self._installed_packages:
            package = self._get_package(installed_package)
            if package and package.filename not in installed_fs:
                self.dbg("Package '{}' not installed".format(installed_package))
                self._install_package(package, save_settings=False)
            else:
                self.dbg("Package '{}' installed".format(installed_package))

        self._untracked_packages = []
        for installed_file in installed_fs:
            package = self._get_package_from_filename(installed_file)
            if not package or package.name not in self._installed_packages:
                self._untracked_packages.append(installed_file)
        if self._untracked_packages:
            self.info("{} package(s) not installed through PackageControl: {}".format(len(self._untracked_packages),
                                                                                      self._untracked_packages))
        outdated = []
        for package_name in self._installed_packages:
            package = self._get_package(package_name)
            if package and self._package_out_of_date(package):
                outdated.append(package_name)
        if outdated:
            self.info("{} package(s) are out of date: {}".format(len(outdated), outdated))

        if self._autoupdate:
            for package_name in outdated:
                package = self._get_package(package_name)
                if package:
                    self._update_package(package)

    def _get_package(self, package_name):
        """
            Returns the package object with the given name if present
        """
        self.dbg("Getting package '{}'".format(package_name))

        possible_packages = [package for package in self._get_available_packages() if package.name == package_name]

        if possible_packages:
            return possible_packages[0]
        else:
            return None

    def _get_package_from_filename(self, file_name):
        """
            Returns the package object with the given filename if present
        """
        self.dbg("Getting package from filename '{}'".format(file_name))

        possible_packages = [package for package in self._get_available_packages() if package.filename == file_name]

        if possible_packages:
            return possible_packages[0]
        else:
            return None

    def _get_available_packages(self, force=False):
        """
            Returns the list of available packages from cache or downloads it if needed
        """
        self.dbg("Getting available packages {}".format("forced" if force else ""))

        if self.__list_updating:
            self.dbg("List already updating, waiting...")
            while self.__list_updating:
                time.sleep(.200)

        try:
            self.__list_updating = True
            cache_path = self.get_package_cache_path(True)
            last_run = self._get_last_run()
            self.dbg("Last run was {}".format(last_run))

            if force or not self._available_packages or not last_run:
                self.dbg("No available packages memory cached or its time to update, getting list from file cache")
                repo = None
                write_cache = False

                if not force and last_run and os.path.isfile(os.path.join(cache_path, "packages.json")):
                    with open(os.path.join(cache_path, "packages.json"), "r") as cache:
                        repo = json.loads(cache.read())
                    write_cache = False
                    self.info("Package list loaded from file cache '{}' ({} packages)".format(repo["name"],
                                                                                              len(repo["packages"])))

                if force or not repo:
                    self.dbg("No available packages cached or its time to update, getting list from ", self._repo_url)
                    req = urllib.request.Request(self._repo_url)
                    with self._urlopener.open(req) as response:
                        repo = json.loads(response.read())
                        if hasattr(req, "redirect"):
                            self.dbg("Request permanently redirected. Changing repository url to:", req.redirect)
                            self._repo_url = req.redirect
                            self._save_settings()
                    write_cache = True
                    self.info("Package list loaded from '{}' ({} packages)".format(repo["name"], len(repo["packages"])))

                self._available_packages = []
                for json_package in repo["packages"]:
                    self._available_packages.append(Package(json_package["name"],
                                                            json_package["version"],
                                                            json_package["description"],
                                                            self._make_date(json_package["date"]),
                                                            json_package["download_url"],
                                                            json_package["filename"]))
                # self.dbg(self._available_packages)

                if write_cache:
                    self.dbg("Writing file cache")
                    with open(os.path.join(cache_path, "packages.json"), "w") as cache_file:
                        cache = {
                            "name": repo["name"],
                            "url": self._repo_url,
                            "packages": [package.to_dict() for package in self._available_packages]
                        }
                        json.dump(cache, cache_file, indent=4)
                    self._save_last_run()

            return self._available_packages
        except Exception as exc:
            self.err("Available packages could not be obtained: {}".format(exc))
        finally:
            self.__list_updating = False

    def _make_date(self, date_str):
        """
            Parses a isoformat datetime string to an datetime-object
            Don't look at this, just don't
        """
        if re.search(r"[+\-]\d\d:\d\d$", date_str):
            date_str = date_str[:-3] + date_str[-2:]
        elif date_str[-5] != '-' and date_str[-5] != '+':
            date_str += "+0000"

        return datetime.datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S%z")

    def _get_last_run(self):
        """
            Reads the time of the last run from file
        """
        cache_path = self.get_package_cache_path(True)

        if not os.path.isfile(os.path.join(cache_path, "last.run")):
            return None

        with open(os.path.join(cache_path, "last.run"), "r") as last_run:
            date_str = last_run.read()

        date = self._make_date(date_str)
        return date if date.replace(tzinfo=None) < datetime.datetime.now() + datetime.timedelta(hours=24) else None

    def _save_last_run(self):
        """
            Writes the time of the last run to a file
        """
        cache_path = self.get_package_cache_path(True)
        with open(os.path.join(cache_path, "last.run"), "w") as last_run:
            last_run.write(datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S%z"))

    def _install_package(self, package, force=False, save_settings=True):
        """
            Downloads the package and adds it to the installed packages list
        """
        self.dbg("Installing package {}".format(package.name))

        package_path = os.path.join(self._get_packages_root(), package.filename)
        if force or not os.path.isfile(os.path.join(package_path)):
            package.download(self._urlopener, self._get_packages_root())
            if package.name not in self._installed_packages:
                self._installed_packages.append(package.name)
            if save_settings:
                self._save_settings()
            self.info("Installed package '{}'".format(package.name))
        else:
            self.warn("Package {} already installed".format(package.name))

    def _remove_package(self, package, save_settings=True):
        """
            Deletes the package from the filesystem and removes it from installed packages list
        """
        self.dbg("Removing package {}".format(package.name))

        package_path = os.path.join(self._get_packages_root(), package.filename)
        self.dbg("Package path: {}".format(package_path))

        if os.path.isfile(package_path):
            os.remove(package_path)
        self._installed_packages.remove(package.name)
        if save_settings:
            self._save_settings()
        self.info("Removed package '{}'".format(package.name))

    def _update_package(self, package, force=False):
        """
            Checks if a update is necessary, replaces the existing packages
        """
        self.dbg("Updating package {}".format(package.name))

        package_path = os.path.join(self._get_packages_root(), package.filename)
        self.dbg("Package path: {}".format(package_path))

        if os.path.isfile(package_path):
            if force or self._package_out_of_date(package):
                package.download(self._urlopener, self._get_packages_root())
                self.info("Updated package '{}'".format(package.name))
            else:
                self.info("Package '{}' up to date".format(package.name))
        else:
            self.warn("Package '{}' not found while updating. Reinstalling".format(package.name))
            self._install_package(package, save_settings=False)

    def _package_out_of_date(self, package):
        """Checks if a package is out of date and returns the result as boolean
        """
        self.dbg("Checking if package is out of date:", package.name)
        package_path = os.path.join(self._get_packages_root(), package.filename)
        if os.path.isfile(package_path):
            stat = os.stat(package_path)
            return stat.st_mtime < package.date.timestamp()

        return False

    def _get_packages_root(self):
        """
            Returns to path to the keypirinha installed package directory
        """
        return kp.installed_package_dir()
