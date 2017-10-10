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

def sort_pipelines(pipelines):
    return sorted(pipelines, key=itemgetter('id'), reverse=True)

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
        ui.info_1('Pipeline:', ui.white, '%d' % pipeline['id'], ui.reset, 'Status:', color, status)

    def display_job(self, job, id):
        status = job['status']
        color = get_color_status(status)
        ui.info('  ', ui.blue, id, ui.reset, 'Job', ui.white, '%d' % (
            job['id']), ui.reset, job['stage'].ljust(8, ' '), color, status.ljust(8, ' '), ui.reset, ' ', job['name'])

    def handle_pipeline(self, pipeline):
        self.display_pipeline(pipeline)
        jobs = self.gl_helper.get_pipeline_jobs(
            self.project_id, pipeline['id'])
        sorted_jobs = sort_jobs(jobs)
        for i, j in enumerate(sorted_jobs, start=1):
            self.display_job(j, i)
        return sorted_jobs

    def ask_for_logs(self, sorted_jobs):
        index = ui.ask_string("display logs? (other commands: accept, retry <id>)")
        index = int(index)
        if index in range(1, len(sorted_jobs) + 1):
            self.log(sorted_jobs[index-1]['id'])

    def list_jobs(self):
        merge_request = self.find_merge_request()
        if not merge_request:
            ui.info("No merge request found")
            return
        self.display_merge_request(merge_request)
        ref = merge_request['source_branch']
        pipelines = self.gl_helper.get_project_pipelines(self.project_id, ref)
        if not pipelines or len(pipelines) == 0:
            self.info("No pipelines")
            return
        sorted_pipelines = sort_pipelines(pipelines)
        if not self.args.all_pipeline:
            print()
            sorted_jobs = self.handle_pipeline(sorted_pipelines[0])
            self.ask_for_logs(sorted_jobs)
            return
        for p in sorted_pipelines:
            print()
            self.handle_pipeline(p)

    def log(self, job_id=None):
        if not job_id:
            job_id = self.args.job_id
        logs = self.gl_helper.get_job_trace(self.project_id, job_id)
        print(logs)

    def main(self):
        self.prepare()
        if self.args.review_command == 'log':
            return self.log()
        self.list_jobs()


def main(args):
    review_action = ReviewAction(args)
    review_action.main()
