"""Protected M1 entrypoint, without legacy DB initialization or ML imports.

Set explicit STETHOFUSE_M1_DATABASE / STETHOFUSE_M1_PRIVATE_STORAGE for the separate
local runtime. Firebase additionally requires approved external ADC configuration.
"""
from app.m1.api import create_app
from app.m1.config import Settings

app = create_app(Settings.from_environment())
