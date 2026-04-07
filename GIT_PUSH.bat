@echo off
echo [1/3] Staging changes...
git add .
echo [2/3] Committing...
git commit -m "Restore industry-sectioned dashboard with sparklines and header UI"
echo [3/3] Pushing to remote...
git push
if %errorlevel% neq 0 (
    echo [ERROR] Push failed. Please check your credentials or network.
) else (
    echo [SUCCESS] Everything is up to date!
)
pause
