AXUS GROUP — Treolan Manager

Это настольное приложение Windows с локальной базой SQLite.

Первый вход:
Логин: admin
Пароль: admin

После входа обязательно смените пароль в будущем (в этой версии пароль администратора хранится хешем).

Настройки Treolan:
- Treolan login/password
- WSDL: https://api.treolan.ru/webservices/treolan.wsdl
- интервал фоновой синхронизации в минутах

Приложение:
- хранит каталог локально в SQLite;
- позволяет искать товары;
- синхронизирует цену, остаток и транзит через GenCatalogV2;
- создаёт backup исходного Excel;
- экспортирует актуальный Excel;
- автоматически обновляется по таймеру.

Для сборки EXE:
1. pip install -r requirements.txt
2. pyinstaller --noconfirm --onefile --windowed --name AXUS-Treolan-Manager app.py
3. EXE будет в dist/AXUS-Treolan-Manager.exe

Для доступа нескольких сотрудников можно расширить users и добавить управление пользователями/ролями.
