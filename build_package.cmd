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

if exist "c:\Program Files (x86)\7-Zip\7z.exe" (
    set "SEVENZIP=c:\Program Files (x86)\7-Zip\7z.exe"
    goto done_sevenzip
)

if exist "c:\Program Files (x86)\7-Zip\7za.exe" (
    set "SEVENZIP=c:\Program Files (x86)\7-Zip\7za.exe"
    goto done_sevenzip
)

if exist "c:\Program Files\7-Zip\7z.exe" (
    set "SEVENZIP=c:\Program Files\7-Zip\7z.exe"
    goto done_sevenzip
)

if exist "c:\Program Files\7-Zip\7za.exe" (
    set "SEVENZIP=c:\Program Files\7-Zip\7za.exe"
    goto done_sevenzip
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
    -x@.gitignore ^
    -x!.gitignore ^
    *
