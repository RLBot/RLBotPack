@rem
@rem Copyright 2015 the original author or authors.
@rem
@rem Licensed under the Apache License, Version 2.0 (the "License");
@rem you may not use this file except in compliance with the License.
@rem You may obtain a copy of the License at
@rem
@rem      https://www.apache.org/licenses/LICENSE-2.0
@rem
@rem Unless required by applicable law or agreed to in writing, software
@rem distributed under the License is distributed on an "AS IS" BASIS,
@rem WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
@rem See the License for the specific language governing permissions and
@rem limitations under the License.
@rem

@if "%DEBUG%" == "" @echo off
@rem ##########################################################################
@rem
@rem  Typeracer startup script for Windows
@rem
@rem ##########################################################################

@rem Set local scope for the variables with windows NT shell
if "%OS%"=="Windows_NT" setlocal

set DIRNAME=%~dp0
if "%DIRNAME%" == "" set DIRNAME=.
set APP_BASE_NAME=%~n0
set APP_HOME=%DIRNAME%..

@rem Add default JVM options here. You can also use JAVA_OPTS and TYPERACER_OPTS to pass JVM options to this script.
set DEFAULT_JVM_OPTS="-Djna.library.path=build/dll" "-Djava.library.path=build/dll"

@rem Find java.exe
if defined JAVA_HOME goto findJavaFromJavaHome

set JAVA_EXE=java.exe
%JAVA_EXE% -version >NUL 2>&1
if "%ERRORLEVEL%" == "0" goto init

echo.
echo ERROR: JAVA_HOME is not set and no 'java' command could be found in your PATH.
echo.
echo Please set the JAVA_HOME variable in your environment to match the
echo location of your Java installation.

goto fail

:findJavaFromJavaHome
set JAVA_HOME=%JAVA_HOME:"=%
set JAVA_EXE=%JAVA_HOME%/bin/java.exe

if exist "%JAVA_EXE%" goto init

echo.
echo ERROR: JAVA_HOME is set to an invalid directory: %JAVA_HOME%
echo.
echo Please set the JAVA_HOME variable in your environment to match the
echo location of your Java installation.

goto fail

:init
@rem Get command-line arguments, handling Windows variants

if not "%OS%" == "Windows_NT" goto win9xME_args

:win9xME_args
@rem Slurp the command line arguments.
set CMD_LINE_ARGS=
set _SKIP=2

:win9xME_args_slurp
if "x%~1" == "x" goto execute

set CMD_LINE_ARGS=%*

:execute
@rem Setup the command line

set CLASSPATH=%APP_HOME%\lib\Typeracer.jar;%APP_HOME%\lib\dll;%APP_HOME%\lib\kotlin-csv-jvm-0.15.2.jar;%APP_HOME%\lib\kotlin-stdlib-jdk8-1.4.31.jar;%APP_HOME%\lib\framework-2.1.0.jar;%APP_HOME%\lib\ejml-fdense-0.38.jar;%APP_HOME%\lib\kotlin-stdlib-jdk7-1.4.31.jar;%APP_HOME%\lib\kotlin-logging-1.7.9.jar;%APP_HOME%\lib\kotlinx-coroutines-core-1.3.2.jar;%APP_HOME%\lib\kotlin-stdlib-1.4.31.jar;%APP_HOME%\lib\kotlin-stdlib-common-1.4.31.jar;%APP_HOME%\lib\jna-platform-4.5.1.jar;%APP_HOME%\lib\jna-4.5.1.jar;%APP_HOME%\lib\flatbuffers-java-1.9.0.1.jar;%APP_HOME%\lib\ejml-core-0.38.jar;%APP_HOME%\lib\jsr305-3.0.2.jar;%APP_HOME%\lib\annotations-13.0.jar;%APP_HOME%\lib\slf4j-api-1.7.29.jar

@rem Execute Typeracer
"%JAVA_EXE%" %DEFAULT_JVM_OPTS% %JAVA_OPTS% %TYPERACER_OPTS%  -classpath "%CLASSPATH%" east.rlbot.MainKt %CMD_LINE_ARGS%

:end
@rem End local scope for the variables with windows NT shell
if "%ERRORLEVEL%"=="0" goto mainEnd

:fail
rem Set variable TYPERACER_EXIT_CONSOLE if you need the _script_ return code instead of
rem the _cmd.exe /c_ return code!
if  not "" == "%TYPERACER_EXIT_CONSOLE%" exit 1
exit /b 1

:mainEnd
if "%OS%"=="Windows_NT" endlocal

:omega
