AXUS GROUP — Treolan Manager / Windows package

Что внутри:
- app.py — настольное приложение;
- AXUS-Treolan-Manager.spec — сборка PyInstaller;
- installer.iss — установщик Inno Setup;
- build-windows.ps1 — локальная сборка на Windows;
- .github/workflows/build.yml — автоматическая сборка EXE + установщика на Windows runner;
- исходный каталог и логотип.

Важно:
В текущей среде ChatGPT нет Windows toolchain (Windows/PyInstaller/Inno Setup), поэтому готовый .exe физически нельзя собрать здесь без эмуляции/Windows runner.
Пакет подготовлен так, чтобы собрать настоящий Windows EXE и Setup.exe на Windows.

Самый простой вариант:
1. Создать новый GitHub repository и загрузить содержимое этой папки.
2. Открыть Actions → Build Windows installer → Run workflow.
3. После сборки скачать два artifacts:
   - AXUS-Treolan-Manager-EXE
   - AXUS-Treolan-Manager-Installer
4. Запускать AXUS-Treolan-Manager-Setup.exe на Windows.

Локально на Windows:
- установить Python 3.12+;
- установить Inno Setup;
- открыть PowerShell в папке проекта;
- выполнить .\build-windows.ps1;
- затем открыть installer.iss через Inno Setup или выполнить iscc.exe installer.iss.

Первый вход:
Логин: admin
Пароль: admin

После первого входа пароль следует изменить.
