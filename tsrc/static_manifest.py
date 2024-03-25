"""Static Manifest objects."""

from dataclasses import dataclass
from typing import Optional, Union

from tsrc.repo import Remote, Repo


@dataclass(frozen=True)
class StaticManifest:
    dest: str
    branch: str
    url: Optional[str] = None
    _origin = "origin"

    def get_origin(self) -> str:
        return type(self)._origin

    origin = property(get_origin)


def repo_from_static_manifest(
    st_m: StaticManifest,
) -> Union[Repo, None]:
    if st_m.url:
        origin = Remote(st_m.origin, st_m.url)
        remotes = []
        remotes.append(origin)
        return Repo(
            dest=st_m.dest,
            remotes=remotes,
            branch=st_m.branch,
        )
    return None
