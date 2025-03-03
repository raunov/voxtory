@echo off
echo Creating virtual environment...
python -m venv venv
echo.

echo Activating virtual environment...
call venv\Scripts\activate

echo Installing dependencies...
python -m pip install -r requirements.txt
echo Done.
