@echo off
:: Activate the virtual environment
call .venv\Scripts\activate

:: Run the Streamlit application
streamlit run translation_webui.py -- --sound mic

:: Pause to keep the console open
pause