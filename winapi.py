# winapi.py — Linux shim
# Re-exports platform_linux so 'from winapi import ...' works unchanged
from platform_linux import list_capturable_windows
from platform_linux import window_frame_rect
from platform_linux import window_under_cursor
from platform_linux import foreign_foreground