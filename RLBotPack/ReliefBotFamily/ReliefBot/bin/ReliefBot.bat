@if "%DEBUG%" == "" @echo off
@rem ##########################################################################
@rem
@rem  ReliefBot startup script for Windows
@rem
@rem ##########################################################################

@rem Set local scope for the variables with windows NT shell
if "%OS%"=="Windows_NT" setlocal

set DIRNAME=%~dp0
if "%DIRNAME%" == "" set DIRNAME=.
set APP_BASE_NAME=%~n0
set APP_HOME=%DIRNAME%..

@rem Add default JVM options here. You can also use JAVA_OPTS and RELIEF_BOT_OPTS to pass JVM options to this script.
set DEFAULT_JVM_OPTS="-Djna.library.path=build/dll" "-Djava.library.path=build/dll" "-XX:+UseG1GC" "-Xms256m"

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

set CLASSPATH=%APP_HOME%\lib\ReliefBot.jar;%APP_HOME%\lib\dll;%APP_HOME%\lib\framework-1.9.0.jar;%APP_HOME%\lib\kotlin-stdlib-jdk8-1.2.60.jar;%APP_HOME%\lib\forms_rt-7.0.3.jar;%APP_HOME%\lib\gson-2.8.1.jar;%APP_HOME%\lib\guava-23.4-jre.jar;%APP_HOME%\lib\ejml-simple-0.35.jar;%APP_HOME%\lib\ejml-dsparse-0.35.jar;%APP_HOME%\lib\ejml-ddense-0.35.jar;%APP_HOME%\lib\jna-platform-4.5.1.jar;%APP_HOME%\lib\jna-4.5.1.jar;%APP_HOME%\lib\py4j-0.10.6.jar;%APP_HOME%\lib\flatbuffers-java-1.9.0.1.jar;%APP_HOME%\lib\kotlin-stdlib-jdk7-1.2.60.jar;%APP_HOME%\lib\kotlin-stdlib-1.2.60.jar;%APP_HOME%\lib\asm-commons-3.0.jar;%APP_HOME%\lib\forms-1.1-preview.jar;%APP_HOME%\lib\jdom-1.0.jar;%APP_HOME%\lib\ejml-fdense-0.35.jar;%APP_HOME%\lib\ejml-cdense-0.35.jar;%APP_HOME%\lib\ejml-zdense-0.35.jar;%APP_HOME%\lib\ejml-core-0.35.jar;%APP_HOME%\lib\jsr305-3.0.2.jar;%APP_HOME%\lib\error_prone_annotations-2.0.18.jar;%APP_HOME%\lib\j2objc-annotations-1.1.jar;%APP_HOME%\lib\animal-sniffer-annotations-1.14.jar;%APP_HOME%\lib\kotlin-stdlib-common-1.2.60.jar;%APP_HOME%\lib\annotations-13.0.jar;%APP_HOME%\lib\asm-tree-3.0.jar;%APP_HOME%\lib\asm-3.0.jar

@rem Execute ReliefBot
"%JAVA_EXE%" %DEFAULT_JVM_OPTS% %JAVA_OPTS% %RELIEF_BOT_OPTS%  -classpath "%CLASSPATH%" tarehart.rlbot.ReliefBotMainKt %CMD_LINE_ARGS%

:end
@rem End local scope for the variables with windows NT shell
if "%ERRORLEVEL%"=="0" goto mainEnd

:fail
rem Set variable RELIEF_BOT_EXIT_CONSOLE if you need the _script_ return code instead of
rem the _cmd.exe /c_ return code!
if  not "" == "%RELIEF_BOT_EXIT_CONSOLE%" exit 1
exit /b 1

:mainEnd
if "%OS%"=="Windows_NT" endlocal

:omega
