""" Entrypoint for Review """

from operator import itemgetter

from .push import get_token, PushAction

import ui

def get_color_status(status):
    color = ui.green
    if status == 'failed':
        color = ui.red
    if status == 'pending' or status == 'created':
        color = ui.blue
    if status == 'skipped':
        color = ui.darkgray
    return color

def get_info_for_merge_status(merge_request):
    if merge_request['merge_status'] == 'can_be_merged':
        return (ui.green, 'no conflict', ui.reset)
    return (ui.red, merge_request['merge_status'], ui.reset)
def sort_jobs(jobs):
    return sorted(jobs, key=itemgetter('stage', 'name'))

class ReviewAction(PushAction):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def display_merge_request(self, merge_request):
        merge_on_success = merge_request['merge_when_pipeline_succeeds']
        wip = merge_request['work_in_progress']
        args = []
        if merge_on_success:
            args.append('merge on success')
        if wip:
            args.append(ui.yellow, 'wip', ui.reset)
        ui.info('Merge request:', merge_request['title'], ui.reset, merge_request['state'], *args)

        ui.info('Merge status :', *get_info_for_merge_status(merge_request))
        ui.info('Author       :', merge_request['author']['name'])
        if merge_request['assignee']:
            ui.info('Assigne      :', merge_request['assignee']['name'])
        ui.info_2(merge_request['web_url'])

    def display_pipeline(self, pipeline):
        status = pipeline['status']
        color = get_color_status(status)
        ui.info_1('Pipeline:', ui.blue, '#%d' % pipeline['id'], ui.reset, 'Status:', color, status)

    def display_job(self, job):
        status = job['status']
        color = get_color_status(status)
        ui.info('Job', '#%d' % (
            job['id']), ui.reset, job['stage'].ljust(8, ' '), color, status.ljust(8, ' '), ui.reset, ' ', job['name'])


    def list_jobs(self):
        merge_request = self.find_merge_request()
        if not merge_request:
            ui.info("No merge request found")
            return
        self.display_merge_request(merge_request)
        ref = merge_request['source_branch']
        pipelines = self.gl_helper.get_project_pipelines(self.project_id, ref)
        add_space = True
        for p in pipelines:
            if add_space:
                print()
            self.display_pipeline(p)
            jobs = self.gl_helper.get_pipeline_jobs(self.project_id, p['id'])
            for j in sort_jobs(jobs):
                self.display_job(j)
            add_space = True

    def main(self):
        self.prepare()
        self.list_jobs()


def main(args):
    review_action = ReviewAction(args)
    review_action.main()
