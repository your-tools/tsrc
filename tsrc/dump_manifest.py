"""
dump_manifest

contains all functions and logic used
in order to obtain or update Manifest dump from current Workspace

SIDE NOTE:
Q: Why puting so much trouble to going through YAML data on each
single operation of Update?
A: It is due to keep as much original data (including comments)
as possible
"""

import hashlib
import re
from collections import OrderedDict
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Union

from ruamel.yaml.comments import CommentedMap

from tsrc.cli import (
    is_match_repo_dest_on_inc_excl,
    resolve_repos_apply_constraints,
    resolve_repos_without_workspace,
)
from tsrc.dump_manifest_args_data import ManifestDataOptions
from tsrc.dump_manifest_helper import ManifestRepoItem
from tsrc.groups_and_constraints_data import GroupsAndConstraints
from tsrc.manifest import Manifest
from tsrc.manifest_common_data import ManifestsTypeOfData
from tsrc.pcs_repo import get_deep_manifest_pcsrepo
from tsrc.repo import Remote, Repo
from tsrc.workspace import Workspace


@dataclass(frozen=True)
class ManifestDumpersOptions:
    delete_repo: bool = True
    add_repo: bool = True  # not implemented
    update_repo: bool = True  # not implemented


class ManifestDumper:
    def __init__(self) -> None:
        pass

    def on_update(
        self,
        y: Union[Dict, List],
        mris: Dict[str, ManifestRepoItem],
        workspace: Union[Workspace, None],
        mdo: ManifestDataOptions,
        opt: ManifestDumpersOptions,
        gac: GroupsAndConstraints,
    ) -> Tuple[Union[Dict, List], bool]:
        """
        if we want to UPDATE existing manifest:

        * Find out if there are some Repos, that should be
        renamed (instead of del(old)+add(new))

        * Apply constraints like Groups, regexes

        Update Repo records in YAML:
        * 1st delete Repo(s) that does not exists
            * also delete Group item
        * 2nd update such Repo(s) that does exists
        * 3rd add new Repo(s) that was not updated

        * finaly return something that can be dumped as YAML
        """
        is_updated: bool = False

        # get Repos to consider
        u_m = Manifest()
        # this will print Warning if Group item is not found
        u_m.apply_config(y, ignore_on_mtod=ManifestsTypeOfData.DEEP)
        repos = resolve_repos_without_workspace(u_m, gac)
        this_m_repo: Optional[Repo] = None

        # get rid of Manifest Repo (Deep Manifest) if requested
        if workspace:
            repos, this_m_repo = self.filter_repos_bo_manifest(
                workspace, mdo.skip_manifest, mdo.only_manifest, repos
            )

        # rename Repos of UPDATE source (early)
        tmp_is_updated: bool
        tmp_is_updated, repos = self._rename_update_source_based_on_dump_source(
            y, mris, repos
        )
        is_updated |= tmp_is_updated

        # we now have Repos, that can be work with, so this is the time to:
        # * apply Group filtering, * 'include_regex', * 'exclude_regex'
        repos, ignored_repos_dests = self._filter_by_groups_and_constraints(
            y, gac, repos
        )

        repos_dests: List[str] = [repo.dest for repo in repos]

        # Dump source: Repo(s)
        # if data are from Workspace, it already contains Group filtering
        # if data comes from RAW dump, it contain all Repos (there cannot be any Groups)
        ds_rs: List[str] = list(mris.keys())

        # UPDATE source: current Manifest's Repo(s)
        us_rs: List[str] = []
        self._walk_yaml_get_repos_keys(y, 0, us_rs, False)

        # correction for 'skip_manifest' so it will not be candidate for deletion
        if this_m_repo:
            if mdo.skip_manifest is True:
                if this_m_repo.dest in us_rs:
                    us_rs.remove(this_m_repo.dest)

        # check if there is some constrain on Repos
        is_constrained: bool = self._is_constrained(us_rs, repos, this_m_repo)

        # start calculating change lists (Add|Remove|Update Repos)
        a_rs: List[str]  # add these Repo(s)
        d_rs: List[str] = []  # remove these Repo(s)
        u_rs: List[str]  # update these Repo(s)

        # check for some constraints applied on Repos
        if is_constrained is True:
            a_rs = list(
                set(ds_rs)
                .difference(us_rs)
                .intersection(repos_dests + ignored_repos_dests)
            )
            u_rs = list(set(ds_rs).intersection(us_rs).intersection(repos_dests))
            if opt.delete_repo is True:
                d_rs = list(set(us_rs).difference(ds_rs).intersection(repos_dests))
        else:
            a_rs = list(set(ds_rs).difference(us_rs))
            u_rs = list(set(ds_rs).intersection(us_rs))
            if opt.delete_repo is True:
                d_rs = list(set(us_rs).difference(ds_rs))

        # 1st A: delete Repo(s) that does not exists
        is_updated_tmp: List[bool] = [False]
        self._walk_yaml_delete_group_items(y, 0, False, False, d_rs, is_updated_tmp)
        is_updated |= is_updated_tmp[0]

        # 1st B: delete also Group Repo items
        is_updated_tmp[0] = False
        self._walk_yaml_delete_repos_items(y, 0, False, d_rs, is_updated_tmp)
        is_updated |= is_updated_tmp[0]

        # 2nd update surch Repo(s) that does exists
        is_updated_tmp[0] = False
        self._walk_yaml_update_repos_items(y, 0, mris, mdo, False, u_rs, is_updated_tmp)
        is_updated |= is_updated_tmp[0]

        # 3rd add new Repo(s) that was not updated
        is_updated_tmp[0] = False
        self._walk_yaml_add_repos_items(y, 0, mris, mdo, False, a_rs, is_updated_tmp)
        is_updated |= is_updated_tmp[0]

        return y, is_updated

    """
    ===========================
    Filter section of all kinds

    ____________________________________
    Filter based on Manifest constraints
    """

    def filter_repos_bo_manifest(
        self,
        workspace: Workspace,
        is_skip: bool,
        is_only: bool,
        repos: List[Repo],
    ) -> Tuple[List[Repo], Optional[Repo]]:
        m_repos, _ = get_deep_manifest_pcsrepo(repos, workspace.config.manifest_url)
        x_repo: Optional[Repo] = None
        if m_repos and m_repos[0] in repos:
            if is_skip is True:
                x_repo = deepcopy(m_repos[0])
                repos.remove(m_repos[0])
            elif is_only is True:
                repos = m_repos
        elif is_only is True:
            repos = []
        return repos, x_repo

    """
    ________________________________
    Filter by Groups and constraints
    """

    def _is_constrained(
        self, us_rs: List[str], repos: List[Repo], this_m_repo: Optional[Repo]
    ) -> bool:
        for dest in us_rs:
            is_found: bool = False
            for repo in repos:
                if repo.dest == dest:
                    is_found = True
                    break
            if is_found is False:
                if this_m_repo and dest == this_m_repo.dest:
                    continue
                return True
        return False

    # flake8: noqa: C901
    def _filter_by_groups_and_constraints(
        self,
        y: Union[Dict, List],
        gac: GroupsAndConstraints,
        repos: List[Repo],
    ) -> Tuple[List[Repo], List[str]]:
        ignored_repos_dests: List[str] = []
        if gac.groups:
            o_repos: List[Repo] = []
            u_m = Manifest()
            # we need new current Manifest with renamed Repos and Group items
            u_m.apply_config(y, ignore_on_mtod=ManifestsTypeOfData.DEEP_ON_UPDATE)
            m_groups: List[str] = []
            if u_m.group_list:
                for gr in u_m.group_list.groups:
                    if gr in gac.groups:
                        m_groups.append(gr)
                for e in u_m.group_list.get_elements(m_groups):
                    o_repos.append(u_m.get_repo(e))
            repos = o_repos
            if u_m.group_list and u_m.group_list.missing_elements:
                for mi in u_m.group_list.missing_elements:
                    for k_r_d, i_r_d in mi.items():
                        if gac.groups and k_r_d in gac.groups:
                            if is_match_repo_dest_on_inc_excl(gac, i_r_d) is True:
                                ignored_repos_dests.append(i_r_d)

        repos = resolve_repos_apply_constraints(repos, gac)

        return repos, ignored_repos_dests

    """
    =================================
    Prepare data for Renaming process
    """

    def _rename_update_source_based_on_dump_source(
        self,
        y: Union[Dict, List],
        mris: Dict[str, ManifestRepoItem],
        repos: List[Repo],  # UPDATE Repos (from Manifest)
    ) -> Tuple[bool, List[Repo]]:
        is_updated: bool = False

        dump_urls_dict: OrderedDict[str, str] = OrderedDict()
        rename_repo_dict: OrderedDict[str, str] = OrderedDict()

        # create URL dictionary
        dump_urls_dict = self._get_dump_url_dict(mris)

        # create 1st shot of dictionary for renaming
        rename_repo_dict = self._get_rename_repo_dict(dump_urls_dict, repos)

        # get rid of colisions
        rename_repo_dict_pre: Dict[str, str] = {}
        rename_repo_dict_post: Dict[str, str] = {}
        rename_repo_dict_pre, rename_repo_dict_post = (
            self._get_pre_and_post_rename_repo_dict(dump_urls_dict, rename_repo_dict)
        )

        # Rename repositories entries
        is_updated_tmp: List[bool] = [False]
        self._walk_yaml_rename_repos_items(
            y, 0, False, rename_repo_dict_pre, repos, is_updated_tmp
        )
        is_updated |= is_updated_tmp[0]
        is_updated_tmp = [False]
        self._walk_yaml_rename_repos_items(
            y, 0, False, rename_repo_dict_post, repos, is_updated_tmp
        )
        is_updated |= is_updated_tmp[0]

        # rename on Group's Repo items
        is_updated_tmp = [False]
        self._walk_yaml_rename_group_items(
            y, 0, False, False, rename_repo_dict_pre, is_updated_tmp
        )
        is_updated |= is_updated_tmp[0]
        is_updated_tmp = [False]
        self._walk_yaml_rename_group_items(
            y, 0, False, False, rename_repo_dict_post, is_updated_tmp
        )
        is_updated |= is_updated_tmp[0]

        return is_updated, repos

    def _get_dump_url_dict(
        self, mris: Dict[str, ManifestRepoItem]
    ) -> "OrderedDict[str, str]":
        dump_urls_dict: OrderedDict[str, str] = OrderedDict()
        for k, v in mris.items():
            if v.remotes:
                for remote in v.remotes:
                    dump_urls_dict[remote.url] = k
        return dump_urls_dict

    def _get_rename_repo_dict(
        self,
        dump_urls_dict: "OrderedDict[str, str]",
        repos: List[Repo],
    ) -> "OrderedDict[str, str]":
        rename_repo_dict: OrderedDict[str, str] = OrderedDict()
        for repo in repos:
            if repo.remotes:
                for remote in repo.remotes:
                    if remote.url in dump_urls_dict:
                        if (
                            repo.dest != dump_urls_dict[remote.url]
                            and repo.dest not in rename_repo_dict  # noqa: W503
                        ):
                            rename_repo_dict[repo.dest] = dump_urls_dict[remote.url]
        return rename_repo_dict

    def _get_pre_and_post_rename_repo_dict(
        self,
        dump_urls_dict: "OrderedDict[str, str]",
        rename_repo_dict: "OrderedDict[str, str]",
    ) -> Tuple[Dict[str, str], Dict[str, str]]:
        rename_repo_dict_pre: Dict[str, str] = {}
        rename_repo_dict_post: Dict[str, str] = {}
        for key, val in rename_repo_dict.items():
            unique_key = key
            offset: int = 0
            # while unique_key in rename_repo_dict.values():
            while unique_key in dump_urls_dict.values():
                # create unique sumplement for key
                unique_key = val + "-" + self._get_sha1_plus(val, offset)[:7]
                offset += 1
            if key != unique_key:
                # repeling colision
                rename_repo_dict_pre[key] = unique_key
                rename_repo_dict_post[unique_key] = val
            else:
                # when no colision, add to the 'post'
                rename_repo_dict_post[key] = val
        return rename_repo_dict_pre, rename_repo_dict_post

    def _get_sha1_plus(self, name: str, p: int = 0) -> str:
        # helps create temporary unique name when renaming
        str_sha1 = hashlib.sha1()
        name = name + str(p)
        str_sha1.update(name.encode("utf-8"))
        return str_sha1.hexdigest()

    """
    =============================================
    Renaming Repositories entries into the Manifest
        by walking through YAML file.
    """

    def _rename_repos_based_on_rrd(
        self,
        y: Dict,
        rrd: Dict[str, str],  # rename Repo Dict
        repos: List[Repo],
        is_updated: List[bool],
    ) -> bool:
        ret_updated: bool = is_updated[0]

        if "dest" in y and y["dest"] in rrd.keys():
            dest = y["dest"]
            if y["dest"] != rrd[dest]:
                ret_updated |= True
            for repo in repos:
                if repo.dest == y["dest"]:
                    # rename in Repo
                    repo.rename_dest(rrd[dest])
            # rename in YAML data
            y["dest"] = rrd[dest]

        return ret_updated

    def _walk_yaml_rename_repos_items_on_dict(
        self,
        y: Union[Dict, List],
        level: int,
        on_repos: bool,
        rrd: Dict[str, str],  # rename Repo Dict
        repos: List[Repo],
        is_updated: List[bool],
    ) -> bool:
        ready_return = True
        for _, key in enumerate(y):
            if isinstance(key, tuple):
                ready_return = False
            if isinstance(key, str):
                if key == "repos" and level == 0:
                    on_repos = True
                elif level == 0:
                    on_repos = False
            self._walk_yaml_rename_repos_items(
                y[key], level + 1, on_repos, rrd, repos, is_updated
            )
        return ready_return

    def _walk_yaml_rename_repos_items(
        self,
        y: Union[Dict, List],
        level: int,
        on_repos: bool,
        rrd: Dict[str, str],  # rename Repo Dict
        repos: List[Repo],
        is_updated: List[bool],
    ) -> None:
        if isinstance(y, dict):
            ready_return = self._walk_yaml_rename_repos_items_on_dict(
                y, level, on_repos, rrd, repos, is_updated
            )
            if ready_return is True:
                return
            items = list(y.items())
            for key in items:
                y.pop(key)
        elif isinstance(y, list):

            for index, item in enumerate(y):
                if on_repos is True and isinstance(item, dict) and "dest" in item:

                    # Rename it here
                    is_updated[0] |= self._rename_repos_based_on_rrd(
                        y[index], rrd, repos, is_updated
                    )

                self._walk_yaml_rename_repos_items(
                    item, level, False, rrd, repos, is_updated
                )

    """
    =============================================
    Renaming Group items of the Manifest
        by walking through YAML file.
    """

    def _walk_yaml_rename_group_items_on_dict(
        self,
        y: Union[Dict, List],
        level: int,
        on_groups: bool,
        on_g_r: bool,
        rrd: Dict[str, str],  # rename Repo Dict
        is_updated: List[bool],
    ) -> bool:
        ready_return = True
        for _, key in enumerate(y):
            if isinstance(key, tuple):
                ready_return = False
            if isinstance(key, str):
                if on_groups is True and level == 2 and key == "repos":
                    on_g_r = True
                elif level == 1:
                    on_g_r = False

                if key == "groups" and level == 0:
                    on_groups = True
                elif level == 0:
                    on_groups = False
                    on_g_r = False
            self._walk_yaml_rename_group_items(
                y[key], level + 1, on_groups, on_g_r, rrd, is_updated
            )
        return ready_return

    def _walk_yaml_rename_group_items(
        self,
        y: Union[Dict, List],
        level: int,
        on_groups: bool,
        on_g_r: bool,
        rrd: Dict[str, str],  # rename Repo Dict
        is_updated: List[bool],
    ) -> None:
        if isinstance(y, dict):
            ready_return = self._walk_yaml_rename_group_items_on_dict(
                y, level, on_groups, on_g_r, rrd, is_updated
            )
            if ready_return is True:
                return
            items = list(y.items())
            for key in items:
                y.pop(key)

        elif isinstance(y, list):
            for index, item in enumerate(y):
                if on_groups is True and on_g_r is True:
                    if item in rrd.keys():
                        # Rename it here
                        y[index] = rrd[item]  # this is it

                self._walk_yaml_rename_group_items(
                    item, level, False, False, rrd, is_updated
                )

    """
    ==============================================
    Obtaining 'dest' of Repositories from Manifest
        by walking through YAML file.
    """

    def _walk_yaml_get_repos_keys_on_dict(
        self, y: Union[Dict, List], level: int, repos_dest: List[str], on_repos: bool
    ) -> bool:
        ready_return = True
        for _, key in enumerate(y):
            if isinstance(key, tuple):
                ready_return = False
            if isinstance(key, str):
                if key == "repos" and level == 0:
                    on_repos = True
                elif level == 0:
                    on_repos = False
            self._walk_yaml_get_repos_keys(y[key], level + 1, repos_dest, on_repos)
        return ready_return

    def _walk_yaml_get_repos_keys(
        self,
        y: Union[Dict, List],
        level: int,
        repos_dest: List[str],
        on_repos: bool,
    ) -> None:
        if isinstance(y, dict):
            ready_return = self._walk_yaml_get_repos_keys_on_dict(
                y, level, repos_dest, on_repos
            )
            if ready_return is True:
                return
            items = list(y.items())
            for key in items:
                y.pop(key)
        elif isinstance(y, list):

            for item in y:
                if on_repos is True and isinstance(item, dict) and "dest" in item:

                    # we have found 'dest' (in Repo), add it then
                    repos_dest.append(item["dest"])

                    self._walk_yaml_get_repos_keys(item, level, repos_dest, on_repos)
                else:
                    self._walk_yaml_get_repos_keys(item, level, repos_dest, False)

    """
    =============================================
    Adding Repositories entries into the Manifest
        by walking through YAML file.
    """
    # TODO: add comments to YAML

    def _add_repos_based_on_mris(
        self,
        y: List,
        a_rs: List[str],
        mris: Dict[str, ManifestRepoItem],
        mdo: ManifestDataOptions,
        is_updated: List[bool],
    ) -> bool:
        ret_updated: bool = is_updated[0]
        for a_r in a_rs:
            if mris[a_r]:
                mri = mris[a_r]

                rr = CommentedMap()
                rr["dest"] = a_r
                if mri.remotes:
                    if len(mri.remotes) == 1 and mri.remotes[0].name == "origin":
                        rr["url"] = mri.clone_url
                    else:
                        rr["remotes"] = self._do_create_on_remotes(mri.remotes)
                if mri.ignore_submodules and mri.ignore_submodules is True:
                    rr["ignore_submodules"] = True
                if mri.branch:
                    rr["branch"] = mri.branch
                if mri.tag:
                    rr["tag"] = mri.tag
                if (not mri.branch and not mri.tag and mri.sha1) or mdo.sha1_on is True:
                    rr["sha1"] = mri.sha1

                # TODO: add comment in form of '\n' just to better separate Repos
                y.append(rr)
                ret_updated = True

        return ret_updated

    def _walk_yaml_add_repos_items_on_dict(
        self,
        y: Union[Dict, List],
        level: int,
        mris: Dict[str, ManifestRepoItem],
        mdo: ManifestDataOptions,
        on_repos: bool,
        a_rs: List[str],  # (to) add: (list of) Repos
        is_updated: List[bool],
    ) -> bool:
        ready_return = True
        for _, key in enumerate(y):
            if isinstance(key, tuple):
                ready_return = False
            if isinstance(key, str):
                if key == "repos" and level == 0:
                    on_repos = True
                elif level == 0:
                    on_repos = False
            self._walk_yaml_add_repos_items(
                y[key], level + 1, mris, mdo, on_repos, a_rs, is_updated
            )
        return ready_return

    def _walk_yaml_add_repos_items(
        self,
        y: Union[Dict, List],
        level: int,
        mris: Dict[str, ManifestRepoItem],
        mdo: ManifestDataOptions,
        on_repos: bool,
        a_rs: List[str],  # (to) add (from) Repos
        is_updated: List[bool],
        dest: Union[str, None] = None,
    ) -> None:
        if isinstance(y, dict):
            ready_return = self._walk_yaml_add_repos_items_on_dict(
                y, level, mris, mdo, on_repos, a_rs, is_updated
            )
            if ready_return is True:
                return
            items = list(y.items())
            for key in items:
                y.pop(key)
        elif isinstance(y, list):

            go_add: bool = False
            if len(y) > 0:
                for item in y:
                    if on_repos is True and isinstance(item, dict) and "dest" in item:

                        go_add = True

                        self._walk_yaml_add_repos_items(
                            item,
                            level,
                            mris,
                            mdo,
                            on_repos,
                            a_rs,
                            is_updated,
                            item["dest"],
                        )
                    else:
                        self._walk_yaml_add_repos_items(
                            item, level, mris, mdo, False, a_rs, is_updated
                        )
            else:  # there are no items at all, therefore we are at the end
                go_add = True

            if go_add is True and on_repos is True:
                # add all Repos in here
                is_updated[0] |= self._add_repos_based_on_mris(
                    y, a_rs, mris, mdo, is_updated
                )

    """
    ===============================================
    Updating Repositories entries into the Manifest
        by walking through YAML file.
    """

    def _delete_on_update_on_items_on_repo(
        self,
        y: Dict,
        d_is: List[str],  # delete (these) items
    ) -> bool:
        ret_updated: bool = False
        for d_i in d_is:
            if y[d_i]:
                del y[d_i]
                ret_updated = True
        return ret_updated

    def _update_on_update_on_items_on_repo(
        self,
        y: Dict,
        mri: ManifestRepoItem,
        mdo: ManifestDataOptions,
        u_is: List[str],  # update (these) items
    ) -> bool:
        ret_updated: bool = False
        for u_i in u_is:
            if (
                u_i == "branch"
                and mri.branch  # noqa: W503
                and y[u_i] != mri.branch  # noqa: W503
            ):
                y[u_i] = mri.branch
                ret_updated = True

            if u_i == "tag" and mri.tag and y[u_i] != mri.tag:
                y[u_i] = mri.tag
                ret_updated = True

            # 'sha1' is only updated on special case
            if u_i == "sha1" and (
                (
                    not mri.branch
                    and not mri.tag  # noqa: W503
                    and mri.sha1  # noqa: W503
                    and y[u_i] != mri.sha1  # noqa: W503
                )
                or (mdo.sha1_on is True and y[u_i] != mri.sha1)  # noqa: W503
                or (
                    mdo.sha1_off is False
                    and (mri.ahead > 0 or mri.behind > 0)
                    and y[u_i] != mri.sha1
                )
            ):
                y[u_i] = mri.sha1
                ret_updated = True
        return ret_updated

    def _add_on_update_on_items_on_repo(
        self,
        y: Dict,
        mri: ManifestRepoItem,
        a_is: List[str],  # add (these) items
    ) -> bool:
        ret_updated: bool = False
        for a_i in a_is:
            if a_i == "branch":
                y[a_i] = mri.branch
                ret_updated = True
            if a_i == "tag":
                y[a_i] = mri.tag
                ret_updated = True
            if a_i == "sha1":
                y[a_i] = mri.sha1
                ret_updated = True
        return ret_updated

    def _remotes_on_update_on_items_on_repo_need_update(
        self,
        y: Dict,
        mri: ManifestRepoItem,
    ) -> bool:
        # return True if update is needed
        need_update: bool = False
        # check case when we have "remotes" in Manifest
        if "remotes" in y and mri.remotes:
            if len(y["remotes"]) != len(mri.remotes):
                need_update = True
            else:
                lyr: List[Remote] = []
                for yr in y["remotes"]:
                    if "name" in yr and "url" in yr:
                        lyr.append(Remote(name=yr["name"], url=yr["url"]))

                for remote in lyr + mri.remotes:
                    if remote not in lyr or remote not in mri.remotes:
                        need_update = True
                        break

        # check case when we have "url" in Manifest
        elif "url" in y:
            if (mri.remotes and len(mri.remotes) > 1) or y["url"] != mri.clone_url:
                need_update = True

        # check if we need to add remotes to Manifest
        else:
            if mri.remotes:
                need_update = True

        return need_update

    def _remotes_on_update_on_items_on_repo(
        self,
        y: Dict,
        mri: ManifestRepoItem,
    ) -> bool:
        # 1st: check if need to update
        need_update: bool = self._remotes_on_update_on_items_on_repo_need_update(y, mri)

        # 2nd: do actual update only when needed
        if need_update is True:
            if "url" in y and mri.remotes:
                if len(mri.remotes) == 1 and mri.remotes[0].name == "origin":
                    # just simple update
                    y["url"] = mri.clone_url
                else:
                    del y["url"]
                    y["remotes"] = self._do_create_on_remotes(mri.remotes)

            elif "remotes" in y and mri.remotes:
                # check if we may want to use plain "url" instead of "remotes"
                if len(mri.remotes) == 1 and mri.remotes[0].name == "origin":
                    del y["remotes"]
                    y["url"] = mri.clone_url
                else:
                    y["remotes"] = self._do_create_on_remotes(mri.remotes)
            else:
                # we need to create such record
                if mri.remotes:
                    if len(mri.remotes) == 1 and mri.remotes[0].name == "origin":
                        y["url"] = mri.clone_url
                    else:
                        y["remotes"] = self._do_create_on_remotes(mri.remotes)

        return need_update

    def _update_on_items_on_repo(
        self,
        y: Dict,
        mri: ManifestRepoItem,
        mdo: ManifestDataOptions,
    ) -> bool:
        ret_updated: bool = False

        c_item: List[str] = []  # current item (only those we want to consider)
        for key in y.keys():
            if key == "branch" or key == "tag" or key == "sha1":
                c_item.append(key)

        # states items (only those we want to consider)
        s_item: List[str] = []
        for key in ["branch", "tag"]:  # "sha1" should used by request
            if (key == "branch" and mri.branch) or (key == "tag" and mri.tag):
                s_item.append(key)
        if not s_item:
            if mri.sha1:
                s_item.append("sha1")
        if "sha1" not in s_item and (
            mdo.sha1_on is True
            or (mdo.sha1_off is False and (mri.behind > 0 or mri.ahead > 0))
        ):
            s_item.append("sha1")

        # add these on item
        a_is: List[str] = list(set(s_item).difference(c_item))

        # remove these on item
        d_is: List[str] = list(set(c_item).difference(s_item))

        # update these on item
        u_is: List[str] = list(set(s_item).intersection(c_item))

        # perform action(s) and check if it gets updated
        ret_updated |= self._delete_on_update_on_items_on_repo(y, d_is)
        ret_updated |= self._update_on_update_on_items_on_repo(y, mri, mdo, u_is)
        ret_updated |= self._add_on_update_on_items_on_repo(y, mri, a_is)

        ret_updated |= self._remotes_on_update_on_items_on_repo(y, mri)

        return ret_updated

    def _update_repos_based_on_mris(
        self,
        y: Dict,
        u_rs: List[str],
        mris: Dict[str, ManifestRepoItem],
        mdo: ManifestDataOptions,
        is_updated: List[bool],
    ) -> bool:
        ret_updated: bool = is_updated[0]

        if "dest" in y and y["dest"] in u_rs:
            dest = y["dest"]
            if mris[dest]:
                ret_updated |= self._update_on_items_on_repo(y, mris[dest], mdo)

        return ret_updated

    def _walk_yaml_update_repos_items_on_dict(
        self,
        y: Union[Dict, List],
        level: int,
        mris: Dict[str, ManifestRepoItem],
        mdo: ManifestDataOptions,
        on_repos: bool,
        u_rs: List[str],  # update (list of) Repos
        is_updated: List[bool],
    ) -> bool:
        ready_return = True
        for _, key in enumerate(y):
            if isinstance(key, tuple):
                ready_return = False
            if isinstance(key, str):
                if key == "repos" and level == 0:
                    on_repos = True
                elif level == 0:
                    on_repos = False
            self._walk_yaml_update_repos_items(
                y[key], level + 1, mris, mdo, on_repos, u_rs, is_updated
            )
        return ready_return

    def _walk_yaml_update_repos_items(
        self,
        y: Union[Dict, List],
        level: int,
        mris: Dict[str, ManifestRepoItem],
        mdo: ManifestDataOptions,
        on_repos: bool,
        u_rs: List[str],  # update (this list of) Repos
        is_updated: List[bool],
    ) -> None:
        if isinstance(y, dict):
            ready_return = self._walk_yaml_update_repos_items_on_dict(
                y, level, mris, mdo, on_repos, u_rs, is_updated
            )
            if ready_return is True:
                return
            items = list(y.items())
            for key in items:
                y.pop(key)
        elif isinstance(y, list):

            for index, item in enumerate(y):
                if on_repos is True and isinstance(item, dict) and "dest" in item:

                    # Update it here
                    is_updated[0] |= self._update_repos_based_on_mris(
                        y[index], u_rs, mris, mdo, is_updated
                    )

                self._walk_yaml_update_repos_items(
                    item, level, mris, mdo, False, u_rs, is_updated
                )

    """
    ===========================================
    Deleting Repositories entries from Manifest
        by walking through YAML file.
    """

    def _walk_yaml_delete_group_items_on_dict(
        self,
        y: Union[Dict, List],
        level: int,
        on_groups: bool,
        on_g_r: bool,
        d_rs: List[str],  # (to) delete: (list of) Repos identified by 'dest'
        is_updated: List[bool],
    ) -> bool:
        ready_return = True
        for _, key in enumerate(y):
            if isinstance(key, tuple):
                ready_return = False
            if isinstance(key, str):
                if on_groups is True and level == 2 and key == "repos":
                    on_g_r = True
                elif level == 1:
                    on_g_r = False

                if key == "groups" and level == 0:
                    on_groups = True
                elif level == 0:
                    on_groups = False
                    on_g_r = False
            self._walk_yaml_delete_group_items(
                y[key], level + 1, on_groups, on_g_r, d_rs, is_updated
            )
        return ready_return

    def _walk_yaml_delete_group_items__on_list(
        self,
        y: Union[Dict, List],
        level: int,
        on_groups: bool,
        on_g_r: bool,
        d_rs: List[str],  # (to) delete: (list of) Repos identified by 'dest'
        is_updated: List[bool],
    ) -> None:
        go_dels: List[int] = []
        for index, item in enumerate(y):
            if on_groups is True and on_g_r is True:
                if item in d_rs:
                    go_dels.append(index)
            self._walk_yaml_delete_group_items(
                item, level, False, False, d_rs, is_updated
            )

        if go_dels:
            # traverse backwards in order not to hurt earlier indexes
            for gd in reversed(go_dels):
                del y[gd]
            is_updated[0] = True

    def _walk_yaml_delete_group_items(
        self,
        y: Union[Dict, List],
        level: int,
        on_groups: bool,
        on_g_r: bool,
        d_rs: List[str],  # (to) delete: (list of) Repos identified by 'dest'
        is_updated: List[bool],
    ) -> None:
        if isinstance(y, dict):
            ready_return = self._walk_yaml_delete_group_items_on_dict(
                y, level, on_groups, on_g_r, d_rs, is_updated
            )
            if ready_return is True:
                return
            items = list(y.items())
            for key in items:
                y.pop(key)

        elif isinstance(y, list):
            self._walk_yaml_delete_group_items__on_list(
                y, level, on_groups, on_g_r, d_rs, is_updated
            )

    """
    ---- Delete Repos items
    """

    def _walk_yaml_delete_repos_items_on_dict(
        self,
        y: Union[Dict, List],
        level: int,
        on_repos: bool,
        d_rs: List[str],  # (to) delete: (list of) Repos identified by 'dest'
        is_updated: List[bool],
    ) -> bool:
        ready_return = True
        for _, key in enumerate(y):
            if isinstance(key, tuple):
                ready_return = False
            if isinstance(key, str):
                if key == "repos" and level == 0:
                    on_repos = True
                elif level == 0:
                    on_repos = False
            self._walk_yaml_delete_repos_items(
                y[key], level + 1, on_repos, d_rs, is_updated
            )
        return ready_return

    def _walk_yaml_delete_repos_items__on_list(
        self,
        y: Union[Dict, List],
        level: int,
        on_repos: bool,
        d_rs: List[str],  # (to) delete: (list of) Repos identified by 'dest'
        is_updated: List[bool],
        dest: Union[str, None] = None,
    ) -> None:
        go_dels: List[int] = []
        for index, item in enumerate(y):
            if on_repos is True and isinstance(item, dict) and "dest" in item:

                # identify item
                if item["dest"] in d_rs:
                    go_dels.append(index)

                self._walk_yaml_delete_repos_items(
                    item,
                    level,
                    on_repos,
                    d_rs,
                    is_updated,
                    item["dest"],
                )
            else:
                self._walk_yaml_delete_repos_items(item, level, False, d_rs, is_updated)

        if go_dels:
            # traverse backwards in order not to hurt earlier indexes
            for gd in reversed(go_dels):
                del y[gd]
            is_updated[0] = True

    def _walk_yaml_delete_repos_items(
        self,
        y: Union[Dict, List],
        level: int,
        on_repos: bool,
        d_rs: List[str],  # (to) delete: (list of) Repos identified by 'dest'
        is_updated: List[bool],
        dest: Union[str, None] = None,
    ) -> None:
        if isinstance(y, dict):
            ready_return = self._walk_yaml_delete_repos_items_on_dict(
                y, level, on_repos, d_rs, is_updated
            )
            if ready_return is True:
                return
            items = list(y.items())
            for key in items:
                y.pop(key)
        elif isinstance(y, list):
            self._walk_yaml_delete_repos_items__on_list(
                y, level, on_repos, d_rs, is_updated, dest
            )

    """
    ==========================================
    Creating by filling data to YAML structure
        from ManifestRepoItem
    """

    def _do_create_on_remotes(self, remotes: List[Remote]) -> List[Dict[str, str]]:
        cs: List[Dict[str, str]] = []  # --> CommentedSeq
        cm: Dict[str, str] = {}  # --> CommentedMap

        for sr in remotes:
            # make sure that "origin" will be first
            # this is important to keep default remote first
            if sr.name == "origin":
                cm = {}
                cm["name"] = sr.name
                cm["url"] = sr.url
                cs.append(cm)
        for sr in remotes:
            if sr.name != "origin":
                cm = {}
                cm["name"] = sr.name
                cm["url"] = sr.url
                cs.append(cm)
        return cs

    def do_create(
        self,
        mris: Dict[str, ManifestRepoItem],
        mdo: ManifestDataOptions,
    ) -> Dict:
        y: Dict[str, Any] = {"repos": []}

        # NOTE: nothing we can do about Group

        for dest, items in mris.items():

            rr = CommentedMap()
            rr["dest"] = dest
            if items.remotes:
                if len(items.remotes) == 1 and items.remotes[0].name == "origin":
                    rr["url"] = items.clone_url
                else:
                    rr["remotes"] = self._do_create_on_remotes(items.remotes)
            if items.ignore_submodules is True:
                rr["ignore_submodules"] = True
            if items.branch:
                rr["branch"] = items.branch
            if items.tag:
                rr["tag"] = items.tag
            if (
                (not items.branch and not items.tag and items.sha1)
                or mdo.sha1_on is True
                or (mdo.sha1_off is False and (items.ahead > 0 or items.behind > 0))
            ):
                rr["sha1"] = items.sha1

            y["repos"].append(rr)
        return y

    """
    ===========================================
    Check YAML data structure if all Repos have
        at least one remote.
    """

    def some_remote_is_missing(self, yy: Union[Dict, List, None]) -> bool:
        tmp_is_remote: List[bool] = [True]
        if yy:
            self._walk_yaml_check_remote_in_repo(yy, 0, tmp_is_remote, False)
        return not tmp_is_remote[0]

    def _walk_yaml_check_remote_in_repo_on_dict(
        self, y: Union[Dict, List], level: int, is_remotes: List[bool], on_repos: bool
    ) -> bool:
        ready_return = True
        for _, key in enumerate(y):
            if isinstance(key, tuple):
                ready_return = False
            if isinstance(key, str):
                if key == "repos" and level == 0:
                    on_repos = True
                elif level == 0:
                    on_repos = False
            self._walk_yaml_check_remote_in_repo(
                y[key], level + 1, is_remotes, on_repos
            )
        return ready_return

    def _walk_yaml_check_remote_in_repo(
        self,
        y: Union[Dict, List],
        level: int,
        is_remotes: List[bool],
        on_repos: bool,
    ) -> None:
        if isinstance(y, dict):
            ready_return = self._walk_yaml_check_remote_in_repo_on_dict(
                y, level, is_remotes, on_repos
            )
            if ready_return is True:
                return
            items = list(y.items())
            for key in items:
                y.pop(key)
        elif isinstance(y, list):

            for item in y:
                if on_repos is True and isinstance(item, dict) and "dest" in item:

                    if not ("remote" in item or "url" in item):
                        is_remotes[0] = False

                    # we have found 'dest' (in Repo), add it then

                    self._walk_yaml_check_remote_in_repo(
                        item, level, is_remotes, on_repos
                    )
                else:
                    self._walk_yaml_check_remote_in_repo(item, level, is_remotes, False)
