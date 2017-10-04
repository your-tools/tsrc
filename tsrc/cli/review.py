""" Entrypoint for Review """

from .push import get_token, PushAction

class ReviewAction(PushAction):
  def __init__(self, *args, **kwargs):
      super().__init__(*args, **kwargs)

  def list_jobs(self):
      print("todo")

  def main(self):
      self.prepare()
      self.list_jobs()


def main(args):
  review_action = ReviewAction(args)
  review_action.main()
