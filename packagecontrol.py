from .lib.package import Package
from .lib.RedirectorHandler import RedirectorHandler
import keypirinha as kp
import keypirinha_net as kpn
import keypirinha_util as kpu
import os
import configparser
import json
import datetime
import re
import time
import traceback
import urllib
import gzip
import sys


class PackageControl(kp.Plugin):
    """Package that provides a means to install, update and remove keypirinha packages
    """
    DEFAULT_REPO = "https://ue.spdns.de/packagecontrol/packages.json"
    DEFAULT_ALT_REPO = "https://ueffel.pythonanywhere.com/packages.json"
    DEFAULT_AUTOUPDATE = True
    DEFAULT_UPDATE_INTERVAL = 12
    PACKAGE_COMMAND = kp.ItemCategory.USER_BASE + 1
    COMMAND_INSTALL = "install"
    COMMAND_REMOVE = "remove"
    COMMAND_UPDATE = "update"
    COMMAND_REINSTALL = "reinstall"
    COMMAND_REINSTALL_UNTRACKED = "reinstall_untracked"
    COMMAND_UPDATE_REPO = "update_repo"
    COMMAND_UPDATE_ALL = "update_all"
    COMMAND_REINSTALL_ALL_UNTRACKED = "reinstall_all_untracked"

    def __init__(self):
        super().__init__()
        self._installed_packages = []
        self._untracked_packages = []
        self._available_packages = []
        self._repo_url = self.DEFAULT_REPO
        self._alt_repo_url = self.DEFAULT_ALT_REPO
        self._autoupdate = self.DEFAULT_AUTOUPDATE
        self._update_interval = self.DEFAULT_UPDATE_INTERVAL
        self._urlopener = self._build_urlopener()
        self.__command_executing = False
        self.__list_updating = False
        self._actions = []

    def on_events(self, flags):
        """Reloads the config when its changed and installs missing packages

        Also rebuild the urlopener if network settings are changed
        """
        if flags & kp.Events.PACKCONFIG:
            self._read_config()
            self._check_installed()

        if flags & kp.Events.NETOPTIONS:
            self.dbg("Network settings changed: rebuilding urlopener")
            self._urlopener = self._build_urlopener()

    def on_start(self):
        """Reads config, checks packages and installs missing packages
        """
        self.dbg("Packages root path:", self._get_packages_root())
        self._read_config()

        self._actions.append(self.create_action(
            name="execute",
            label="Execute command",
            short_desc="Executes the selected package command"
        ))
        self._actions.append(self.create_action(
            name="visit_homepage",
            label="Visit homepage of the package",
            short_desc="Opens the browser"
        ))

        self.set_actions(self.PACKAGE_COMMAND, self._actions)

        # Adding PackageControl itself, so updating is possible
        if os.path.dirname(__file__).endswith("PackageControl.keypirinha-package") \
                and "Keypirinha-PackageControl" not in self._installed_packages:
            self._installed_packages.append("Keypirinha-PackageControl")

        self._check_installed()

    def on_catalog(self):
        """Adds the commands to the catalog
        """
        catalog = []

        install_cmd = self.create_item(
            category=self.PACKAGE_COMMAND,
            label="PackageControl: Install Package",
            short_desc="Installs a new packages from the repositiory",
            target=self.COMMAND_INSTALL,
            args_hint=kp.ItemArgsHint.REQUIRED,
            hit_hint=kp.ItemHitHint.NOARGS
        )
        catalog.append(install_cmd)

        uninstall_cmd = self.create_item(
            category=self.PACKAGE_COMMAND,
            label="PackageControl: Remove Package",
            short_desc="Removes already installed packages",
            target=self.COMMAND_REMOVE,
            args_hint=kp.ItemArgsHint.REQUIRED,
            hit_hint=kp.ItemHitHint.NOARGS
        )
        catalog.append(uninstall_cmd)

        update_cmd = self.create_item(
            category=self.PACKAGE_COMMAND,
            label="PackageControl: Update Package",
            short_desc="Updates already installed packages to the latest version",
            target=self.COMMAND_UPDATE,
            args_hint=kp.ItemArgsHint.REQUIRED,
            hit_hint=kp.ItemHitHint.NOARGS
        )
        catalog.append(update_cmd)

        reinstall_cmd = self.create_item(
            category=self.PACKAGE_COMMAND,
            label="PackageControl: Reinstall Package",
            short_desc="Removes packages and installs them again from the repository",
            target=self.COMMAND_REINSTALL,
            args_hint=kp.ItemArgsHint.REQUIRED,
            hit_hint=kp.ItemHitHint.NOARGS
        )
        catalog.append(reinstall_cmd)

        reinstall_untracked_cmd = self.create_item(
            category=self.PACKAGE_COMMAND,
            label="PackageControl: Reinstall untracked package from repository",
            short_desc="Reinstalls a package that was not installed through PackageControl from the repository",
            target=self.COMMAND_REINSTALL_UNTRACKED,
            args_hint=kp.ItemArgsHint.REQUIRED,
            hit_hint=kp.ItemHitHint.NOARGS
        )
        catalog.append(reinstall_untracked_cmd)

        update_repo_cmd = self.create_item(
            category=self.PACKAGE_COMMAND,
            label="PackageControl: Update Repository List",
            short_desc="Updates the list of packages from the repository",
            target=self.COMMAND_UPDATE_REPO,
            args_hint=kp.ItemArgsHint.FORBIDDEN,
            hit_hint=kp.ItemHitHint.NOARGS
        )
        catalog.append(update_repo_cmd)

        update_all_cmd = self.create_item(
            category=self.PACKAGE_COMMAND,
            label="PackageControl: Update All Packages",
            short_desc="Updates all currently installed packages to the latest version from the repository",
            target=self.COMMAND_UPDATE_ALL,
            args_hint=kp.ItemArgsHint.FORBIDDEN,
            hit_hint=kp.ItemHitHint.NOARGS
        )
        catalog.append(update_all_cmd)

        reinstall_all_untracked_cmd = self.create_item(
            category=self.PACKAGE_COMMAND,
            label="PackageControl: Reinstalls all untracked package from repository",
            short_desc="Reinstalls all packages that were not installed through PackageControl from the repository",
            target=self.COMMAND_REINSTALL_ALL_UNTRACKED,
            args_hint=kp.ItemArgsHint.FORBIDDEN,
            hit_hint=kp.ItemHitHint.NOARGS
        )
        catalog.append(reinstall_all_untracked_cmd)

        self.set_catalog(catalog)

    def on_suggest(self, user_input, items_chain):
        """Suggests a list of packages for the command
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

        if items_chain[0].target() == self.COMMAND_INSTALL:
            self.dbg("Suggesting packages to install")
            packages = [package for package in self._get_available_packages()
                        if package.name not in self._installed_packages]
        elif items_chain[0].target() == self.COMMAND_REMOVE or items_chain[0].target() == self.COMMAND_UPDATE \
                or items_chain[0].target() == self.COMMAND_REINSTALL:
            self.dbg("Suggesting packages to update/remove/reinstall")
            packages = [package for package in self._get_available_packages()
                        if package.name in self._installed_packages]
        elif items_chain[0].target() == self.COMMAND_REINSTALL_UNTRACKED:
            self.dbg("Suggesting packages to reinstall untracked")
            packages = [package for package in self._get_available_packages()
                        if package.filename in self._untracked_packages]

        for package in packages:
            package_item = items_chain[0].clone()
            package_item.set_short_desc(package.description if package.description else "no description")
            package_item.set_args("{} (by @{})".format(package.name, package.owner))
            package_item.set_data_bag(package.name)
            suggestions.append(package_item)

        self.set_suggestions(suggestions)

    def on_execute(self, item, action):
        """Executes the command
        """
        self.dbg("on_execute() item: {}, action: {}".format(item, action))
        self.dbg("args:", item.raw_args())

        if self.__command_executing:
            self.warn("Another command is already executing, doing nothing")
            return

        try:
            self.__command_executing = True
            if action is not None and action.name() == "visit_homepage":
                package = self._get_package(item.data_bag())
                if package.homepage:
                    self.dbg(urllib.parse.urlparse(package.homepage).scheme)
                    if urllib.parse.urlparse(package.homepage).scheme in ("http", "https"):
                        kpu.shell_execute(package.homepage)
                    else:
                        self.warn("Package homepage is not a web link:", package.homepage)
                else:
                    self.warn("Package homepage not set")
                return

            if item.target() == self.COMMAND_INSTALL:
                self._install_package(self._get_package(item.data_bag()))
            elif item.target() == self.COMMAND_REMOVE:
                self._remove_package(self._get_package(item.data_bag()))
            elif item.target() == self.COMMAND_UPDATE:
                self._update_package(self._get_package(item.data_bag()))
            elif item.target() == self.COMMAND_REINSTALL:
                package = self._get_package(item.data_bag())
                self._remove_package(package, save_settings=False)
                self._install_package(package)
            elif item.target() == self.COMMAND_REINSTALL_UNTRACKED:
                self._install_package(self._get_package(item.data_bag()), force=True)
            elif item.target() == self.COMMAND_UPDATE_REPO:
                self._get_available_packages(True)
                self._check_installed()
            elif item.target() == self.COMMAND_UPDATE_ALL:
                self._get_available_packages(True)
                for package_name in self._installed_packages:
                    package = self._get_package(package_name)
                    self._update_package(package)
                self.info("Updating all packages finished")
            elif item.target() == self.COMMAND_REINSTALL_ALL_UNTRACKED:
                for untracked in self._untracked_packages:
                    package = self._get_package_from_filename(untracked)
                    if package:
                        self._install_package(package, force=True, save_settings=False)
                    else:
                        self.info("Package not found in repository:", untracked)
                self._save_settings()
                self.info("Reinstalling all untracked packages finished")
        except Exception:
            self.err("Error occurred while executing command '{}'\n{}".format(item, traceback.format_exc()))
        finally:
            self.__command_executing = False

    def _read_config(self):
        """Reads the repo url and the installed packages list from the config
        """
        self.dbg("Reading config")
        settings = self.load_settings()

        self._debug = settings.get_bool("debug", "main", False)

        old_repo_url = self._repo_url
        self._repo_url = settings.get("repository", "main", self.DEFAULT_REPO)
        self.dbg("repo_url:", self._repo_url)

        self._alt_repo_url = settings.get("alternative_repository", "main", self.DEFAULT_ALT_REPO)
        self.dbg("alt_repo_url:", self._alt_repo_url)

        if old_repo_url != self._repo_url:
            self._get_available_packages(True)

        self._installed_packages = list(set(settings.get_multiline("installed_packages", "main")))
        self.dbg("installed_packages:", self._installed_packages)

        self._autoupdate = settings.get_bool("autoupdate", "main", self.DEFAULT_AUTOUPDATE)
        self.dbg("autoupdate:", self._autoupdate)

        self._update_interval = settings.get_float("update_interval", "main", self.DEFAULT_UPDATE_INTERVAL)
        self.dbg("update_interval:", self._update_interval)

    def _build_urlopener(self):
        """Creates an urllib opener with 2 custom handlers and returns it
        """
        self.dbg("Building urlopener")
        user_agent = "{}/{} python-{}/{}.{}.{}".format(kp.name(),
                                                       kp.version_string(),
                                                       urllib.__name__,
                                                       sys.version_info[0],
                                                       sys.version_info[1],
                                                       sys.version_info[2])
        opener = kpn.build_urllib_opener(extra_handlers=[RedirectorHandler()])
        opener.addheaders = [("Accept-Encoding", "gzip"), ("User-Agent", user_agent)]
        return opener

    def _save_settings(self):
        """Save the user config file with all installed packages
        """
        self.dbg("Saving settings")

        save_path = os.path.join(kp.user_config_dir(), "{}.ini".format(self.package_full_name()))
        config = configparser.ConfigParser()
        config.read(save_path)

        if "main" not in config:
            config.add_section("main")

        if "repository" in config["main"] and config["main"]["repository"] != self._repo_url:
            config["main"]["repository"] = self._repo_url

        if "alternative_repository" in config["main"] and config["main"]["alternative_repository"] != self._alt_repo_url:
            config["main"]["alternative_repository"] = self._alt_repo_url

        config["main"]["installed_packages"] = "\n{}".format("\n".join(self._installed_packages))

        with open(save_path, "w") as ini_file:
            config.write(ini_file)

    def _check_installed(self):
        """Check if installed packages from the config are really present

        Also makes a list of packages that are installed but not in the config (untracked)
        """
        self.dbg("Checking installed packages")

        installed_fs = [file for file in os.listdir(self._get_packages_root())
                        if os.path.isfile(os.path.join(self._get_packages_root(), file))
                        and file.endswith(".keypirinha-package")]
        self.dbg("Filesystem packages:", installed_fs)

        for installed_package in self._installed_packages:
            package = self._get_package(installed_package)
            if package and package.filename not in installed_fs:
                self.dbg("Package not installed:", installed_package)
                self._install_package(package, save_settings=False)
            else:
                self.dbg("Package installed:", installed_package)

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
        """Returns the package object with the given name if present
        """
        self.dbg("Getting package:", package_name)

        return next((package for package in self._get_available_packages() if package.name == package_name), None)

    def _get_package_from_filename(self, file_name):
        """Returns the package object with the given filename if present
        """
        self.dbg("Getting package from filename:", file_name)
        return next((package for package in self._get_available_packages() if package.filename == file_name), None)

    def _get_available_packages(self, force=False):
        """Returns the list of available packages from cache or downloads it if needed
        """
        self.dbg("Getting available packages", "forced" if force else "")

        if self.__list_updating:
            self.dbg("List already updating, waiting...")
            while self.__list_updating:
                time.sleep(.200)

        try:
            self.__list_updating = True
            cache_path = self.get_package_cache_path(True)
            last_run = self._get_last_run()
            self.dbg("Last run was", last_run)

            if force or not self._available_packages or not last_run:
                self.dbg("No available packages memory cached or its time to update, getting list from file cache")
                repo = None
                write_cache = False

                if not force and last_run and os.path.isfile(os.path.join(cache_path, "packages.json")):
                    with open(os.path.join(cache_path, "packages.json"), "r") as cache:
                        repo = json.load(cache)
                    write_cache = False
                    self.info("Package list loaded from file cache '{}' ({} packages)".format(repo["name"],
                                                                                              len(repo["packages"])))

                if force or not repo:
                    self.dbg("No available packages cached or its time to update, getting list from the net")
                    tries = 4
                    repos = [self._repo_url, self._alt_repo_url]
                    while tries > 0:
                        try:
                            repo_url = repos[tries % 2]
                            self.dbg("Try to get list from", repo_url)
                            req = urllib.request.Request(repo_url)
                            with self._urlopener.open(req) as response:
                                if response.info().get("Content-Encoding") == "gzip":
                                    repo = json.loads(gzip.decompress(response.read()).decode())
                                else:
                                    repo = json.loads(response.read().decode())
                                tries = 0
                                if hasattr(req, "redirect"):
                                    self.info("Request permanently redirected. Changing repository url to:",
                                              req.redirect)
                                    if tries % 2 == 0:
                                        self._repo_url = req.redirect
                                    else:
                                        self._alt_repo_url = req.redirect
                                    self._save_settings()
                        except Exception as ex:
                            tries -= 1
                            if tries > 0:
                                self.dbg("Error while obtaining the packages trying again...:", traceback.format_exc())
                                self.err("Error while obtaining the packages trying again...")
                            else:
                                raise ex

                    write_cache = True
                    self.info("Package list loaded from '{}' ({} packages)".format(repo["name"], len(repo["packages"])))

                self._available_packages = []
                for json_package in repo["packages"]:
                    self._available_packages.append(Package(json_package["name"],
                                                            json_package["version"],
                                                            json_package["description"],
                                                            self._make_date(json_package["date"]),
                                                            json_package["download_url"],
                                                            json_package["filename"],
                                                            json_package["owner"] if "owner" in json_package else "",
                                                            json_package["homepage"]
                                                            if "homepage" in json_package else ""))
                self.dbg(self._available_packages)

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
        except Exception:
            self.err("Available packages could not be obtained:\n", traceback.format_exc())
        finally:
            self.__list_updating = False

    def _make_date(self, date_str):
        """Parses a isoformat datetime string to an datetime-object

        Don't look at this, just don't
        """
        if re.search(r"[+\-]\d\d:\d\d$", date_str):
            date_str = date_str[:-3] + date_str[-2:]
        elif date_str[-5] != '-' and date_str[-5] != '+':
            date_str += "+0000"

        return datetime.datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S%z")

    def _get_last_run(self):
        """Reads the time of the last run from file
        """
        cache_path = self.get_package_cache_path(True)

        if not os.path.isfile(os.path.join(cache_path, "last.run")):
            return None

        with open(os.path.join(cache_path, "last.run"), "r") as last_run:
            date_str = last_run.read()

        try:
            date = self._make_date(date_str)
            return date \
                if date.replace(tzinfo=None)+datetime.timedelta(hours=self._update_interval) > datetime.datetime.utcnow() \
                else None
        except Exception:
            self.warn(traceback.format_exc())
            return None


    def _save_last_run(self):
        """Writes the time of the last run to a file
        """
        cache_path = self.get_package_cache_path(True)
        with open(os.path.join(cache_path, "last.run"), "w") as last_run:
            last_run.write(datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S%z"))

    def _install_package(self, package, force=False, save_settings=True):
        """Downloads the package and adds it to the installed packages list
        """
        self.dbg("Installing package:", package.name)

        package_path = os.path.join(self._get_packages_root(), package.filename)
        if force or not os.path.isfile(os.path.join(package_path)):
            package.download(self._urlopener, self._get_packages_root())
            if package.name not in self._installed_packages:
                self._installed_packages.append(package.name)
            if save_settings:
                self._save_settings()
            self.info("Installed package '{}'".format(package.name))
        else:
            self.warn("Package '{}' already installed".format(package.name))

    def _remove_package(self, package, save_settings=True):
        """Deletes the package from the filesystem and removes it from installed packages list
        """
        self.dbg("Removing package:", package.name)

        package_path = os.path.join(self._get_packages_root(), package.filename)
        self.dbg("Package path:", package_path)

        if os.path.isfile(package_path):
            os.remove(package_path)
        self._installed_packages.remove(package.name)
        if save_settings:
            self._save_settings()
        self.info("Removed package:", package.name)

    def _update_package(self, package, force=False):
        """Checks if a update is necessary, replaces the existing packages
        """
        self.dbg("Updating package:", package.name)

        package_path = os.path.join(self._get_packages_root(), package.filename)
        self.dbg("Package path:", package_path)

        if os.path.isfile(package_path):
            if force or self._package_out_of_date(package):
                package.download(self._urlopener, self._get_packages_root())
                self.info("Updated package:", package.name)
            else:
                self.info("Package up to date:", package.name)
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

    @staticmethod
    def _get_packages_root():
        """Returns to path to the keypirinha installed package directory
        """
        return kp.installed_package_dir()
