@echo off
title Blender Live Preview
echo ====================================================
echo   Khoi dong Blender 5.2 voi che do Live Preview Sync
echo ====================================================
echo Blender dang mo, hay giu nguyen cua so Blender nay.
echo Moi khi AI viet code ve 3D, Blender se lap tuc cap nhat tren man hinh!
echo ====================================================

"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" --python "%~dp0live_sync.py"
