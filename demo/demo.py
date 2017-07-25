""" Main script to run the demo.

See demo.yml for configuring the demo
"""

import argparse
import subprocess
import textwrap
import time

import path
import ruamel.yaml

from tsrc import ui
import tsrc.gitlab
import tsrc.cli.push


TSRC_URL = "https://tanker.io/open-source/tsrc"


class DemoMaker():
    def __init__(self):
        contents = path.Path("demo.yml").text()
        self.config = ruamel.yaml.safe_load(contents)
        token = tsrc.cli.push.get_token()
        self.gitlab_helper = tsrc.gitlab.GitLabHelper(self.http_url, token)
        self.tmp_path = path.Path("tmp")
        self.work_path = self.tmp_path.joinpath("work")
        self.srv_path = self.tmp_path.joinpath("srv")

    @property
    def project(self):
        return self.config["gitlab"]["project"]

    @property
    def ssh_url(self):
        return self.config["gitlab"]["ssh"]

    @property
    def http_url(self):
        return self.config["gitlab"]["http"]

    def chapter(self, *args):
        ui.info()
        _, text = ui.process_tokens(args)
        ui.info(*args)
        ui.info(ui.reset, "=" * len(text), end="\n\n")
        time.sleep(3)

    def step(self, *args, cwd):
        ui.info(ui.green, "$", ui.reset, ui.bold, *args, end="\n\n")
        time.sleep(5)
        subprocess.run(args, cwd=cwd)

    def clean(self):
        self.tmp_path.rmtree_p()
        self.tmp_path.mkdir()

    def setup(self):
        self.clean()
        self.re_init_repos()
        self.init_manifest()

    def repo_path(self, name):
        return

    def re_init_repos(self):
        project_path = self.srv_path.joinpath(self.project)
        for name in ["manifest", "bar", "baz"]:
            repo_path = project_path.joinpath(name)
            repo_path.makedirs()
            tsrc.git.run_git(repo_path, "init", quiet=True)
            repo_path.joinpath(f"{name}.txt").write_text(f"This is {name}\n")
            tsrc.git.run_git(repo_path, "add", f"{name}.txt", quiet=True)
            tsrc.git.run_git(repo_path, "commit", "--message", f"initial {name}", quiet=True)
            origin_url = f"{self.ssh_url}:{self.project}/{name}.git"
            tsrc.git.run_git(repo_path, "remote", "add", "origin", origin_url, quiet=True)
            tsrc.git.run_git(repo_path, "push", "--force", "origin", "master", quiet=True)
            ui.dot()
            tsrc.git.run_git(repo_path, "push", "--delete", "origin", "me/new-feature",
                             raises=False)
            ui.dot()
        bar_path = project_path.joinpath("bar")
        bar_path.joinpath("top.txt").write_text("This goes no the top\n")
        tsrc.git.run_git(bar_path, "add", "top.txt", quiet=True)
        tsrc.git.run_git(bar_path, "commit", "--message", "add top.txt", quiet=True)
        tsrc.git.run_git(bar_path, "push", "origin", "master", quiet=True)
        ui.dot()

    def init_manifest(self):
        manifest_path = path.Path(f"{self.srv_path}/{self.project}/manifest")
        manifest_contents = textwrap.dedent(f"""\
        gitlab:
          url: {self.http_url}

        repos:
        - src: {self.project}/bar
          url: {self.ssh_url}:{self.project}/bar
          copy:
            - src: top.txt
              dest: top.txt

        - src: {self.project}/baz
          url: {self.ssh_url}:{self.project}/baz
        """)
        manifest_path.joinpath("manifest.yml").write_text(manifest_contents)
        tsrc.git.run_git(manifest_path, "add", "manifest.yml", quiet=True)
        tsrc.git.run_git(manifest_path, "commit", "--message", "add the manifest", quiet=True)
        tsrc.git.run_git(manifest_path, "push", "origin", "master", quiet=True)
        ui.dot(last=True)

    def run(self):
        self.work_path.mkdir_p()

        self.chapter("Initialize workspace")
        manifest_url = self.config["gitlab"]["ssh"] + f":{self.project}/manifest.git"
        self.step("tsrc", "init", manifest_url, cwd=self.work_path)

        self.chapter("Synchronize workspace")

        # Push a commit else where:
        bar_path = self.srv_path.joinpath(self.project, "bar")
        new_txt = bar_path.joinpath("new.txt")
        new_txt.write_text("this is new\n")
        tsrc.git.run_git(bar_path, "add", "new.txt", quiet=True)
        tsrc.git.run_git(bar_path, "commit", "--message", "new feature", quiet=True)
        tsrc.git.run_git(bar_path, "push", "origin", "master", quiet=True)

        self.step("tsrc", "sync", cwd=self.work_path)

        self.chapter("Making a pull request")
        ui.info(ui.green, "*", ui.reset, ui.bold, "Working on a new feature")
        baz_path = self.work_path.joinpath(self.project, "baz")
        tsrc.git.run_git(baz_path, "checkout", "-b", "me/new-feature")
        my_txt = baz_path.joinpath("my.txt")
        my_txt.write_text("this is mine\n")
        tsrc.git.run_git(baz_path, "add", "my.txt")
        tsrc.git.run_git(baz_path, "commit", "--message", "my new feature")
        ui.info()
        self.step("tsrc", "push", cwd=baz_path)

        self.chapter("Accepting the pull request")
        self.step("tsrc", "push", "--accept", cwd=baz_path)

    def make_demo(self):
        ui.info("Welcome to tsrc demo!")
        time.sleep(1)
        ui.info("Please wait while we get things ready", ui.ellipsis)
        self.setup()
        ui.info()
        time.sleep(1)
        ui.info("Here we go:")
        time.sleep(2)
        self.run()
        ui.info()
        time.sleep(3)
        ui.info("More info on", TSRC_URL)
        time.sleep(1)
        ui.info("Thanks for watching!")


def main():
    demo_maker = DemoMaker()
    demo_maker.make_demo()


if __name__ == "__main__":
    main()
