@echo off
:: Activate the virtual environment
call .venv\Scripts\activate

:: Run the Streamlit application
streamlit run main.py
:: Pause to keep the console open
pause