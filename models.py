from dataclasses import dataclass, field


@dataclass
class Job:
    company: str
    id: str               # unique within the company
    title: str
    location: str
    url: str
    posted: str = ""      # human-readable posting time, if the source gives one
    description: str = "" # plain text; may be filled in later by a fetcher's describe()
    meta: dict = field(default_factory=dict)  # source-specific data needed by describe()

    @property
    def uid(self) -> str:
        return f"{self.company}:{self.id}"
