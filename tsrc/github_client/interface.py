from typing import List, Sequence, Optional
import abc

# Note: users are just strings in GitHub API


class PullRequest(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def get_number(self) -> int:
        pass

    def get_short_description(self) -> str:
        return "#" + str(self.get_number())

    def get_html_url(self) -> str:
        pass

    @abc.abstractmethod
    def update(self, *, base: Optional[str], title: Optional[str]) -> None:
        pass

    @abc.abstractmethod
    def assign(self, assignee: str) -> None:
        pass

    @abc.abstractmethod
    def request_reviewers(self, reviewers: List[str]) -> None:
        pass

    @abc.abstractmethod
    def merge(self) -> None:
        pass

    @abc.abstractmethod
    def close(self) -> None:
        pass


class Repository(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def find_pull_requests(self, *, state: str, head: str) -> Sequence[PullRequest]:
        pass

    @abc.abstractmethod
    def get_default_branch(self) -> str:
        pass

    @abc.abstractmethod
    def create_pull_request(self, *, title: str, head: str, base: str) -> PullRequest:
        pass


class Client(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def get_repository(self, owner: str, name: str) -> Repository:
        pass
