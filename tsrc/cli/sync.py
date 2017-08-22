""" Entry point for tsrc sync """


from tsrc import ui
import tsrc.cli


def main(args):
    workspace = tsrc.cli.get_workspace(args)
    workspace.update_manifest()
    workspace.load_manifest()
    workspace.clone_missing()
    workspace.set_remotes()
    workspace.sync()
    workspace.copy_files()
    ui.info("Done", ui.check)
