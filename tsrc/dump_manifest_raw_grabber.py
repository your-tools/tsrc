import os
from copy import deepcopy
from pathlib import Path
from typing import List, Tuple, Union

import cli_ui as ui

from tsrc.cli import is_match_repo_dest_on_inc_excl
from tsrc.dump_manifest_args import DumpManifestArgs
from tsrc.dump_manifest_args_data import DumpManifestOperationDetails
from tsrc.executor import process_items
from tsrc.repo import Repo
from tsrc.repo_grabber import RepoGrabber
from tsrc.utils import erase_last_line


class ManifestRawGrabber:
    # using paralelism; how it is done:
    # 1st: obtain all '.git' paths and just save it to List
    # 2nd: call 'process_items' to get GIT stats
    def __init__(self, a: DumpManifestArgs, dfp: Path) -> None:
        self.a = a
        self.dump_from_path = dfp
        if self.dump_from_path.is_dir() is False:
            raise Exception(f"Such Path is not found: {self.dump_from_path}")
        ui.info_1(
            *[
                "Checking Path (recursively) for Repos from:",
                ui.blue,
                self.dump_from_path,
            ]
        )

    def _may_reduce_path(
        self, int_path: Union[List[str], None], this_path: List[str]
    ) -> List[str]:
        # remove '.git' from the end and also last dir if exists
        len_this_path = len(this_path)
        if len_this_path >= 2:
            del this_path[-2:]  # keep also name of the dir wehre is '.git'
        elif len_this_path == 1:
            del this_path[-1]

        # find maximum common Path
        if int_path:
            len_int_path = len(int_path)
            len_this_path = len(this_path)

            # cut-down 'int_path' to length of 'this_path'
            if len_int_path > len_this_path:
                tmp_int_path = deepcopy(int_path)
                for c, _ in reversed(list(enumerate(tmp_int_path))):
                    if c > len_this_path - 1:
                        del int_path[c]

            # check from backwards and delete that does not match
            tmp_list = deepcopy(int_path)
            for i, _ in reversed(list(enumerate(tmp_list))):
                if tmp_list[i] != this_path[i]:
                    del int_path[i]
        else:
            int_path = deepcopy(this_path)
        return int_path

    def get_common_path(self, use_path: Path) -> Union[List[str], None]:
        # return maximum common Path

        int_path: Union[List, None] = None  # intersectioned path
        some_int_path: bool = False  # should we return something?
        # for root, dirs, files in os.walk(this_path):
        for root, _, _ in os.walk(use_path):
            path = root.split(os.sep)
            name = os.path.basename(root)

            do_continue: bool = False
            # do not consider dot-started dirs, but '.git'
            for i, p in enumerate(path):
                if i > 0 and p != ".git" and p.startswith(".") is True:
                    do_continue = True
                    break
            if do_continue is True:
                continue

            # we may have found Repo
            if name == ".git":
                this_path = deepcopy(path)
                if len(path) >= 2:
                    int_path = self._may_reduce_path(int_path, this_path)
                    some_int_path = True

        if not int_path and some_int_path is True:
            return ["."]  # try current directory when empty

        return int_path

    def _grab_on_repo_path(
        self, path: List[str], common_path: Union[List[str], None]
    ) -> Tuple[Union[Path, None], Union[str, None]]:

        use_path: Union[Path, None] = None
        use_path_list: Union[List[str], None] = None
        this_path = deepcopy(path)
        if len(path) >= 2:
            del this_path[-1]
            use_path = Path(os.sep.join(this_path))
            use_path_list = this_path

        if use_path and use_path_list and common_path:
            use_path_clean = deepcopy(use_path_list)
            for index, _ in reversed(list(enumerate(use_path_list))):
                if (
                    len(common_path) > index
                    and use_path_list[index] == common_path[index]  # noqa: W503
                ):
                    del use_path_clean[index]

            if use_path_clean:
                return Path(use_path), os.sep.join(use_path_clean)

        return None, None

    def common_path_is_ready(
        self, dump_from_path: Path
    ) -> Tuple[Union[List[str], None], DumpManifestOperationDetails]:
        # grab_save_path: Union[Path, None] = None
        # common_path had to be removed from every Repo find later
        common_path = self.get_common_path(dump_from_path)
        if common_path:
            common_path_path = os.sep.join(common_path)
            ui.info_2(f"Using Repo(s) COMMON PATH on: '{common_path_path}'")

            # call args handling (include data and check yet again)
            self.a.dmod = self.a.consider_common_path(common_path)

        return common_path, self.a.dmod

    def grab(self, num_jobs: int) -> Tuple[List[Repo], DumpManifestArgs]:

        # let us understand the situation we are in
        ui.info_1("Note: it is not possible to obtain anything regarding Groups")

        # verify and fetch 'common_path' ('grab_save_path' optionaly too)
        common_path, self.a.dmod = self.common_path_is_ready(self.dump_from_path)

        repos_paths: List[Repo] = []  # here 'dest' is used as Path

        for root, _, _ in os.walk(self.dump_from_path):
            path = root.split(os.sep)
            name = os.path.basename(root)

            do_continue: bool = False
            for i, p in enumerate(path):
                if i > 0 and p != ".git" and p.startswith(".") is True:
                    do_continue = True
                    break

            if do_continue is True:
                continue
            if name == ".git":
                repo_path, clean_dest = self._grab_on_repo_path(path, common_path)
                if not repo_path:
                    continue

                # check constraints (except for Groups and singular_remote)
                if (
                    clean_dest
                    and is_match_repo_dest_on_inc_excl(  # noqa: W503
                        self.a.gac, os.path.basename(clean_dest)
                    )
                    is False
                ):
                    continue

                # create pseudo-Repo for 'process_items' to eat
                if repo_path and clean_dest:
                    this_repo = Repo(
                        dest=clean_dest, remotes=[], _grabbed_from_path=repo_path
                    )
                    repos_paths.append(this_repo)

        if repos_paths:
            # we have now list of Paths of possible Repos
            repo_grabber = RepoGrabber(common_path)
            ui.info_1(f"Checking for Repos: out of possible {len(repos_paths)} paths")
            process_items(repos_paths, repo_grabber, num_jobs=num_jobs)
            erase_last_line()
            ui.info_2(
                f"Found {len(repo_grabber.repos)} Repos out of {len(repos_paths)} possible paths"
            )

            return repo_grabber.repos, self.a
        else:
            ui.info_2("No Repos were found")
            return [], self.a
