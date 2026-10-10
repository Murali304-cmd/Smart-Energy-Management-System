@echo off
title Smart Home Energy Management System (SEMS) Launcher
echo ======================================================================
echo Launching Smart Home Energy Management System (SEMS)
echo ======================================================================
echo.

set OPENBLAS_NUM_THREADS=1
set OMP_NUM_THREADS=1
set MKL_NUM_THREADS=1
set NUMEXPR_NUM_THREADS=1
set VECLIB_MAXIMUM_THREADS=1

echo Starting SEMS Application on http://127.0.0.1:8000 ...
start "SEMS Server" cmd /k "cd /d "%~dp0" && set OPENBLAS_NUM_THREADS=1 && set OMP_NUM_THREADS=1 && python -m uvicorn server:app --host 127.0.0.1 --port 8000"

timeout /t 3 /nobreak >nul

echo Opening browser to http://localhost:8000 ...
start http://localhost:8000

echo.
echo ======================================================================
echo SEMS is now active!
echo Web Application: http://localhost:8000
echo API Docs:        http://127.0.0.1:8000/docs
echo ======================================================================
pause
