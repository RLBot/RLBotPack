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

set CLASSPATH=%APP_HOME%\lib\ReliefBot.jar;%APP_HOME%\lib\dll;%APP_HOME%\lib\framework-2.1.0.jar;%APP_HOME%\lib\ActionServer-1.1.1.jar;%APP_HOME%\lib\TwitchBrokerClient-1.0.0.jar;%APP_HOME%\lib\kotlin-stdlib-jdk8-1.3.71.jar;%APP_HOME%\lib\ejml-fdense-0.38.jar;%APP_HOME%\lib\jna-platform-4.5.1.jar;%APP_HOME%\lib\jna-4.5.1.jar;%APP_HOME%\lib\flatbuffers-java-1.9.0.1.jar;%APP_HOME%\lib\spring-boot-starter-web-1.5.22.RELEASE.jar;%APP_HOME%\lib\spring-boot-starter-tomcat-1.5.22.RELEASE.jar;%APP_HOME%\lib\springfox-swagger2-2.9.2.jar;%APP_HOME%\lib\springfox-swagger-ui-2.9.2.jar;%APP_HOME%\lib\jackson-datatype-threetenbp-2.6.4.jar;%APP_HOME%\lib\hibernate-validator-5.3.6.Final.jar;%APP_HOME%\lib\validation-api-1.1.0.Final.jar;%APP_HOME%\lib\swagger-annotations-2.0.0.jar;%APP_HOME%\lib\logging-interceptor-2.7.5.jar;%APP_HOME%\lib\okhttp-2.7.5.jar;%APP_HOME%\lib\gson-fire-1.8.3.jar;%APP_HOME%\lib\gson-2.8.1.jar;%APP_HOME%\lib\threetenbp-1.3.5.jar;%APP_HOME%\lib\kotlin-stdlib-jdk7-1.3.71.jar;%APP_HOME%\lib\kotlin-stdlib-1.3.71.jar;%APP_HOME%\lib\ejml-core-0.38.jar;%APP_HOME%\lib\jsr305-3.0.2.jar;%APP_HOME%\lib\spring-boot-starter-1.5.22.RELEASE.jar;%APP_HOME%\lib\jackson-databind-2.8.11.3.jar;%APP_HOME%\lib\spring-webmvc-4.3.25.RELEASE.jar;%APP_HOME%\lib\spring-web-4.3.25.RELEASE.jar;%APP_HOME%\lib\tomcat-embed-websocket-8.5.43.jar;%APP_HOME%\lib\tomcat-embed-core-8.5.43.jar;%APP_HOME%\lib\tomcat-embed-el-8.5.43.jar;%APP_HOME%\lib\springfox-swagger-common-2.9.2.jar;%APP_HOME%\lib\swagger-models-1.5.20.jar;%APP_HOME%\lib\swagger-annotations-1.5.20.jar;%APP_HOME%\lib\springfox-schema-2.9.2.jar;%APP_HOME%\lib\springfox-spring-web-2.9.2.jar;%APP_HOME%\lib\springfox-spi-2.9.2.jar;%APP_HOME%\lib\springfox-core-2.9.2.jar;%APP_HOME%\lib\guava-20.0.jar;%APP_HOME%\lib\classmate-1.4.0.jar;%APP_HOME%\lib\spring-plugin-metadata-1.2.0.RELEASE.jar;%APP_HOME%\lib\spring-plugin-core-1.2.0.RELEASE.jar;%APP_HOME%\lib\spring-boot-starter-logging-1.5.22.RELEASE.jar;%APP_HOME%\lib\logback-classic-1.1.11.jar;%APP_HOME%\lib\jcl-over-slf4j-1.7.26.jar;%APP_HOME%\lib\jul-to-slf4j-1.7.26.jar;%APP_HOME%\lib\log4j-over-slf4j-1.7.26.jar;%APP_HOME%\lib\slf4j-api-1.7.26.jar;%APP_HOME%\lib\mapstruct-1.2.0.Final.jar;%APP_HOME%\lib\jackson-core-2.8.10.jar;%APP_HOME%\lib\okio-1.6.0.jar;%APP_HOME%\lib\kotlin-stdlib-common-1.3.71.jar;%APP_HOME%\lib\annotations-13.0.jar;%APP_HOME%\lib\spring-boot-autoconfigure-1.5.22.RELEASE.jar;%APP_HOME%\lib\spring-boot-1.5.22.RELEASE.jar;%APP_HOME%\lib\spring-context-4.3.25.RELEASE.jar;%APP_HOME%\lib\spring-aop-4.3.25.RELEASE.jar;%APP_HOME%\lib\spring-beans-4.3.25.RELEASE.jar;%APP_HOME%\lib\spring-expression-4.3.25.RELEASE.jar;%APP_HOME%\lib\spring-core-4.3.25.RELEASE.jar;%APP_HOME%\lib\snakeyaml-1.17.jar;%APP_HOME%\lib\jboss-logging-3.3.0.Final.jar;%APP_HOME%\lib\jackson-annotations-2.9.5.jar;%APP_HOME%\lib\tomcat-annotations-api-8.5.43.jar;%APP_HOME%\lib\commons-logging-1.2.jar;%APP_HOME%\lib\byte-buddy-1.8.12.jar;%APP_HOME%\lib\logback-core-1.1.11.jar

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
