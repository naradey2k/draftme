from pydantic import BaseModel


class Contact(BaseModel):
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    linkedin: str | None = None
    github: str | None = None
    website: str | None = None
    location: str | None = None
    other_links: list[str] = []


class Experience(BaseModel):
    company: str = ""
    title: str = ""
    start: str = ""
    end: str | None = None
    bullets: list[str]


class WorkExperience(BaseModel):
    employer: str | None = None
    title: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    bullet_points: list[str] = []


class Education(BaseModel):
    institution: str = ""
    degree: str = ""
    field: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    year: str | None = None
    notes: list[str] = []


class SkillsData(BaseModel):
    technical: list[str] = []
    languages: list[str] = []
    certifications: list[str] = []
    awards: list[str] = []


class Project(BaseModel):
    name: str | None = None
    short_description: str | None = None
    url: str | None = None
    key_bullet_points: list[str] = []


class CVData(BaseModel):
    name: str
    contact: Contact
    summary: str | None = None
    experience: list[Experience]
    education: list[Education]
    skills: list[str]
    certifications: list[str] = []
    awards: list[str] = []
    languages: list[str] = []
    projects: list[Project] = []
    publications: list[str] = []
    raw_text: str
