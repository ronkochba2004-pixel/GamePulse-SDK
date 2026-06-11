from enum import Enum


class EventCategory(str, Enum):
    SYSTEM = "system"
    PROGRESSION = "progression"
    ECONOMY = "economy"
    GAMEPLAY = "gameplay"
    SOCIAL = "social"
    ERROR = "error"
    CUSTOM = "custom"


class Platform(str, Enum):
    WINDOWS = "windows"
    MACOS = "macos"
    LINUX = "linux"
    IOS = "ios"
    ANDROID = "android"
    WEB = "web"
    CONSOLE = "console"
    UNKNOWN = "unknown"


class Severity(str, Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    FATAL = "fatal"


class SessionEndReason(str, Enum):
    NORMAL = "normal"
    CRASH = "crash"
    RAGE_QUIT = "rage_quit"
    TIMEOUT = "timeout"
    BACKGROUND = "background"
