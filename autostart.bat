@echo off
REM Makes DB start in voice mode every time you log in to Windows.
REM Run again with "remove" to undo:  autostart.bat remove
set "LINK=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\DB.bat"
if /i "%1"=="remove" (del "%LINK%" 2>nul & echo DB will no longer start at login. & pause & exit /b 0)
(echo @echo off
 echo start "DB" /min "%~dp0start_db_voice.bat") > "%LINK%"
echo DB will now start at login. Run "autostart.bat remove" to undo.
pause
