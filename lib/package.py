import json
import os


class Package:
    """Represents a keypirinha package
    """
    def __init__(self, name, version, desc, date, dl_url, filename):
        self.name = name
        self.version = version
        self.description = desc
        self.date = date
        self.download_url = dl_url
        self.filename = filename if filename else "{}.keypirinha-package".format(name)

    def download(self, opener, directory):
        """Downloads the file from download_url and saves it to the given directory
        """
        with opener.open(self.download_url) as dl, \
                open(os.path.join(directory, self.filename), "wb") as package:
            for chunk in iter(lambda: dl.read(4096), ""):
                if not chunk:
                    break
                package.write(chunk)
        os.utime(os.path.join(directory, self.filename), times=(self.date.timestamp(), self.date.timestamp()))

    def to_dict(self):
        """Creates a dictionary from the package object
        """
        obj = {
            "download_url": self.download_url,
            "name": self.name,
            "filename": self.filename,
            "date": self.date.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "description": self.description,
            "version": self.version
        }
        return obj

    def to_json(self):
        """Create json string from the package object
        """
        return json.dumps(self.to_dict(), sort_keys=True, indent=4)

    def __repr__(self):
        """Readable representation of the package object (json)
        """
        return self.to_json()
