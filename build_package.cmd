@echo off
set PACKAGE_NAME=PackageControl

set SEVENZIP=
where 7z > nul 2>&1
if not errorlevel 1 (
    set SEVENZIP=7z
    goto done_sevenzip
)

where 7za > nul 2>&1
if not errorlevel 1 (
    set SEVENZIP=7za
    goto done_sevenzip
)

for /f "tokens=3,*" %%v in ('reg query HKCU\Software\7-Zip /v Path') do (
    echo %%v %%w
    if exist "%%v %%w7z.exe" (
        set "SEVENZIP=%%v %%w7z.exe"
        goto done_sevenzip
    )
    if exist "%%v %%w7za.exe" (
        set "SEVENZIP=%%v %%w7za.exe"
        goto done_sevenzip
    )
)

if not defined SEVENZIP (
    echo 7zip not found
    exit /b 1
)

:done_sevenzip

:pack
if exist %PACKAGE_NAME%.keypirinha-package (
    del %PACKAGE_NAME%.keypirinha-package
)
echo Using "%SEVENZIP%" to pack
"%SEVENZIP%" a -mx9 ^
    -tzip "%PACKAGE_NAME%.keypirinha-package" ^
    -x!%~nx0 ^
    -xr!.git ^
    -xr!usage.gif ^
    -xr@.gitignore ^
    -x!.gitignore ^
    *
