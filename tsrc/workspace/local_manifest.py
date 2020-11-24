import abc

import tsrc
import tsrc.manifest


class LocalManifest(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def update(self) -> None:
        pass

    @abc.abstractmethod
    def get_manifest(self) -> tsrc.manifest.Manifest:
        pass
