from typing import Sequence, Optional
import abc
import tsrc


class User(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def get_id(self) -> int:
        pass

    @abc.abstractmethod
    def get_name(self) -> str:
        pass


class MergeRequest(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def get_id(self) -> int:
        pass

    def get_short_description(self) -> str:
        return "!" + str(self.get_id())

    @abc.abstractmethod
    def get_title(self) -> str:
        pass

    @abc.abstractmethod
    def get_web_url(self) -> str:
        pass

    @abc.abstractmethod
    def set_title(self, title: str) -> None:
        pass

    @abc.abstractmethod
    def set_target_branch(self, branch: str) -> None:
        pass

    @abc.abstractmethod
    def set_assignee(self, assignee: User) -> None:
        pass

    @abc.abstractmethod
    def set_approvers(self, approvers: Sequence[User]) -> None:
        pass

    @abc.abstractmethod
    def accept(self) -> None:
        pass

    @abc.abstractmethod
    def close(self) -> None:
        pass

    @abc.abstractmethod
    def save(self) -> None:
        pass

    @abc.abstractmethod
    def remove_source_branch(self) -> None:
        pass


class Project(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def find_merge_requests(
        self, *, state: str, source_branch: str
    ) -> Sequence[MergeRequest]:
        pass

    @abc.abstractmethod
    def get_default_branch(self) -> str:
        pass

    @abc.abstractmethod
    def create_merge_request(
        self, *, source_branch: str, target_branch: str, title: str
    ) -> MergeRequest:
        pass

    @abc.abstractmethod
    def search_members(self, query: str) -> Sequence[User]:
        pass


class Group(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def search_members(self, query: str) -> Sequence[User]:
        pass


class Client(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def get_group(self, group_name: str) -> Optional[Group]:
        pass

    @abc.abstractmethod
    def get_features_list(self) -> Optional[Sequence[str]]:
        pass

    @abc.abstractmethod
    def get_project(self, name: str) -> Project:
        pass


class ProjectNotFound(tsrc.Error):
    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__("No project found with this name: %s" % self.name)
