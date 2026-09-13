from enum import StrEnum


class PoemGenre(StrEnum):
    ANCIENT = "古体诗"
    QUATRAIN = "绝句"
    REGULATED = "律诗"
    CI = "词"
    QU = "曲"
    YUEFU = "乐府"
    OTHER = "其他"


class VerificationStatus(StrEnum):
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"


class TagDimension(StrEnum):
    SUBJECT = "subject"
    SEASON = "season"
    TIME = "time"
    WEATHER = "weather"
    MOOD = "mood"
    THEME = "theme"
    ATMOSPHERE = "atmosphere"

