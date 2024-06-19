"""
Manifest Common

Takes control over finding all provided Groups
in order to report the exception 'GroupNotFound' properly
(as Groups can be matched on more than 1 place)

Not only finding the Groups, but also obtaining
proper list of Repositories from them.
"""

import functools
import sys
from typing import Any, Callable, List, Tuple, TypeVar, Union

import cli_ui as ui
from mypy_extensions import KwArg, VarArg

from tsrc.errors import Error
from tsrc.groups_to_find import GroupsToFind
from tsrc.manifest import Manifest
from tsrc.repo import Repo
from tsrc.workspace import Workspace

# for compatibility reasons
if sys.version_info >= (3, 10):
    from typing import TypeAlias
else:
    from typing_extensions import TypeAlias


class ManifestGroupError(Error):
    pass


# class ManifestGroupNotFound(Exception):
class ManifestGroupNotFound(ManifestGroupError):
    def __init__(self, nf_group: str):
        self.nf_group = nf_group
        message = f"No such group: '{self.nf_group}'"
        super().__init__(message)


T = TypeVar("T")
_RecFn: TypeAlias = Union[T, Callable[[VarArg(Any), KwArg(Any)], T]]
RecFn: TypeAlias = Callable[[VarArg(Any), KwArg(Any)], _RecFn]


def catch_manifest_group_not_found(
    f: Callable,
) -> Union[Any, Callable[[VarArg(Any), KwArg(Any)], Callable[..., RecFn]]]:
    @functools.wraps(f)
    def func(
        *args: List[Any], **kwargs: List[List[Any]]
    ) -> Union[Any, Callable[[VarArg(Any), KwArg(Any)], Callable[..., RecFn]]]:
        try:
            return f(*args, **kwargs)
        except ManifestGroupNotFound as e:
            ui.error(e)
            sys.exit(1)

    return func


class ManifestGetRepos:
    def __init__(
        self,
        workspace: Workspace,
        manifest: Manifest,
        on_manifest_only: bool = False,
        clone_all_repos: bool = False,
    ) -> None:
        """
        look for repos in given manifest in regard of groups.
        get only such repos, that are intersection with
        repos of local groups and repos of required groups.

        'on_manifest_only' = signal that we do not care about
        matching the local groups
        and want to only consider repos of groups from manifest
        (this is particaly useful when checking Future Manifest alone)
        """
        self.workspace = workspace
        self.manifest = manifest
        self.on_manifest_only = on_manifest_only
        self.clone_all_repos = clone_all_repos

        # internal variables
        self._local_m = self.workspace.local_manifest.get_manifest()
        self.must_find_all_groups: bool = False

    def by_groups(
        self,
        gtf: GroupsToFind,
        must_find_all_groups: bool = False,
    ) -> Tuple[List[Repo], bool, GroupsToFind]:
        self.gtf = gtf
        self.must_find_all_groups = must_find_all_groups
        repos: List[Repo] = []
        if self.gtf.groups:
            repos = self._with_groups()
        else:
            repos = self._without_groups()
        return repos, self.must_find_all_groups, self.gtf

    def _with_groups(self) -> List[Repo]:
        m_group_items = []
        if (
            self.gtf.groups
            and self.manifest.group_list  # noqa noqa: W503
            and self.manifest.group_list.groups  # noqa noqa: W503
        ):
            groups_for_m = list(
                set(self.gtf.groups).intersection(self.manifest.group_list.groups)
            )
            self._with_groups_missing_group(groups_for_m)

            # no need to check again after passing exception
            if self.must_find_all_groups is True:
                self.must_find_all_groups = False

            # keep founded groups
            if groups_for_m:
                self.gtf.found_these(groups_for_m)

            m_group_items = list(self.manifest.group_list.get_elements(groups_for_m))
        else:
            for i in self.manifest.get_repos(all_=True):
                m_group_items.append(i.dest)

        if self.on_manifest_only is False:
            return self._with_groups_consider_local(m_group_items)

        repos: List[Repo] = []
        for _, item in enumerate(m_group_items):
            repos.append(self.manifest.get_repo(item))
        return repos

    @catch_manifest_group_not_found
    def _with_groups_missing_group(self, groups_for_m: List[str]) -> None:
        if self.gtf.groups:
            missing_groups: List[str] = []
            missing_groups = list(set(self.gtf.groups).difference(groups_for_m))
            if missing_groups and self.must_find_all_groups is True:
                for missing_group in missing_groups:
                    if self.gtf.was_found(missing_group) is False:
                        raise ManifestGroupNotFound(missing_group)
                        return

    def _with_groups_consider_local(self, m_group_items: List[str]) -> List[Repo]:
        if (
            self.gtf.groups
            and self._local_m.group_list  # noqa: W503
            and self._local_m.group_list.groups  # noqa: W503
        ):
            groups_for_w = list(
                set(self.gtf.groups).intersection(self._local_m.group_list.groups)
            )
            w_group_items = self._local_m.group_list.get_elements(groups_for_w)
        else:
            return self._local_m.get_repos(all_=True)

        repos: List[Repo] = []
        found_items = list(set(w_group_items).intersection(m_group_items))
        for item in found_items:
            repos.append(self.manifest.get_repo(item))
        return repos

    def _without_groups(self) -> List[Repo]:
        found_items = []
        if self.clone_all_repos:
            return self.manifest.get_repos(all_=True)
        else:
            if self.on_manifest_only is True:
                # in this case, we have nothing to match,
                # as groups configured in manifest is just that
                return self.manifest.get_repos(all_=True)

            # 1st: check if we have some groups configured for Workspace
            if self.workspace.config.repo_groups:
                m_group_items: List[str] = []
                if self.manifest.group_list and self.manifest.group_list.groups:
                    m_group_items = self.manifest.group_list.get_elements(
                        list(self.workspace.config.repo_groups),
                        ignore_if_group_not_found=True,
                    )
                    # TODO: if not found any items, should not we use all?
                else:
                    # m_group_items = self.manifest.get_repos(all_=True)
                    for repo in self.manifest.get_repos(all_=True):
                        m_group_items.append(repo.dest)
                pass
            else:
                # we need to consider all groups in such case
                return self.manifest.get_repos(all_=True)

            if self._local_m.group_list and self._local_m.group_list.groups:
                w_group_items = self._local_m.group_list.get_elements(
                    self.workspace.config.repo_groups
                )
            else:
                return self._local_m.get_repos(all_=True)
            found_items = list(set(w_group_items).intersection(m_group_items))

        repos: List[Repo] = []
        for item in found_items:
            repos.append(self.manifest.get_repo(item))
        return repos
