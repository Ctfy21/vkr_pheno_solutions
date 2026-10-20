# PhenoPlant — Платформа цифрового фенотипирования растений

Веб-приложение для автоматизированного сбора, структурирования и анализа фенотипических данных растений с поддержкой стандартов BrAPI v2.1 и CropOntology.

## Технологический стек

| Компонент | Технология |
|-----------|-----------|
| Backend | Python 3.12, FastAPI, Motor (async MongoDB), Pydantic v2 |
| Frontend | Vue.js 3, TypeScript, Tailwind CSS 4, Vite |
| Database | MongoDB 7 (+ GridFS для изображений) |
| Auth | Keycloak 26.0 (OIDC/OAuth 2.0) |
| Infrastructure | Proxmox VE, MicroK8s (Kubernetes), Docker |
| CV/ML | OpenCV, NumPy |

## Быстрый старт

### Требования

- Ubuntu 24.04 LTS (VM или физический сервер)
- Минимум 4 GB RAM, 4 CPU, 30 GB диск
- MicroK8s (`snap install microk8s --classic`)
- Docker (`apt install docker.io`)
- Node.js 22+ (`snap install node --classic`)

### 1. Установка MicroK8s и аддонов

```bash
snap install microk8s --classic
microk8s enable dns storage ingress metrics-server
```

### 2. Сборка и деплой MongoDB

```bash
microk8s kubectl apply -f k8s/mongodb.yaml
```

### 3. Настройка Keycloak

```bash
microk8s kubectl apply -f k8s/keycloak.yaml
```

После запуска пода Keycloak создайте realm и клиент:

```bash
# Подключитесь к Keycloak поду
KC_POD=$(microk8s kubectl get pods -l app=keycloak -o jsonpath='{.items[0].metadata.name}')

# Создайте realm phenoplant
microk8s kubectl exec $KC_POD -- /opt/keycloak/bin/kcadm.sh config credentials \
  --server http://localhost:8080 --realm master --user admin --password admin

microk8s kubectl exec $KC_POD -- /opt/keycloak/bin/kcadm.sh create realms \
  -s realm=phenoplant -s enabled=true -s registrationAllowed=true \
  -s loginWithEmailAllowed=true -s accessTokenLifespan=3600

# Создайте клиент phenoplant-app
microk8s kubectl exec $KC_POD -- /opt/keycloak/bin/kcadm.sh create clients \
  -r phenoplant -s clientId=phenoplant-app -s publicClient=true \
  -s 'redirectUris=["*"]' -s directAccessGrantsEnabled=true

# Создайте роли
for role in admin researcher observer; do
  microk8s kubectl exec $KC_POD -- /opt/keycloak/bin/kcadm.sh create roles \
    -r phenoplant -s name=$role
done
```

### 4. Сборка Backend

```bash
cd backend
docker build -t phenoplant-backend:latest .
docker save phenoplant-backend:latest | microk8s ctr image import -
microk8s kubectl apply -f ../k8s/backend.yaml
```

### 5. Сборка Frontend

```bash
cd frontend
npm ci
npm run build
docker build -t phenoplant-frontend:latest .
docker save phenoplant-frontend:latest | microk8s ctr image import -
microk8s kubectl apply -f ../k8s/frontend.yaml
```

### 6. Настройка Ingress

```bash
microk8s kubectl apply -f k8s/ingress.yaml
```

### 7. Наполнение каталога CropOntology

```bash
python3 scripts/seed_cropontology.py --url http://<IP>/api --email admin@phenoplant.ru --password <password>
```

## Проверка работоспособности

```bash
# Статус подов
microk8s kubectl get pods

# Должно быть:
# mongodb-0                    1/1  Running
# phenoplant-backend-xxx       1/1  Running  (2 реплики)
# phenoplant-frontend-xxx      1/1  Running
# keycloak-xxx                 1/1  Running

# Проверка API
curl http://<IP>/api/health
# {"status":"ok"}
```

Откройте `http://<IP>` в браузере. Зарегистрируйте первого пользователя.

---

## Руководство пользователя

### Вход и регистрация

1. Откройте платформу в браузере
2. Нажмите «Регистрация», введите имя, email и пароль
3. После входа вы попадёте на главную панель (Dashboard)

Если вы уже залогинены — платформа автоматически перенаправит на Dashboard.

### Выбор исследовательской программы

Программа — это верхнеуровневый контекст работы (аналог workspace).

1. В **боковом меню** сверху отображается текущая программа
2. Нажмите на неё → откроется экран выбора программы
3. Выберите существующую или создайте новую (название, аббревиатура, культура, руководитель)
4. Выбранная программа сохраняется и восстанавливается при следующем входе

### Создание эксперимента

1. Перейдите в **Эксперименты** → **Новый эксперимент**
2. **Шаг 1 — Информация**: название, тип (фенотипирование/селекция/стресс/генотипирование), даты, камера
3. **Шаг 2 — Переменные**: выберите переменные из каталога CropOntology (например, Plant height CO_321:0000020)
4. **Шаг 3 — Растения**: добавьте растения вручную или импортируйте CSV (name, germplasm_id, position, treatment)
5. **Шаг 4 — Обзор**: проверьте и создайте

Эксперимент автоматически привязывается к текущей программе.

### Загрузка изображений

**Массовая загрузка:**
1. Откройте эксперимент → **Загрузить фото**
2. Укажите название папки (например, «День 7 — вид сбоку»)
3. Перетащите файлы или выберите через файловый диалог
4. Имена файлов автоматически сопоставляются с растениями (если имя файла содержит имя растения; при нескольких совпадениях выбирается самое длинное имя)
5. Файлы отправляются пакетами по 20 штук; в списке результатов видны отклонённые файлы и дубликаты

Для каждого снимка сервер:
- определяет формат по сигнатуре файла (JPEG, PNG, TIFF, WebP, BMP), а не по заголовку браузера, и ограничивает размер (`IMAGE_MAX_MB`, по умолчанию 25 МБ);
- вычисляет SHA-256 и не сохраняет повторно тот же файл в эксперименте;
- определяет время съёмки: EXIF `DateTimeOriginal` (с часовым поясом `OffsetTimeOriginal`), иначе дата изменения файла из браузера, иначе время загрузки; источник сохраняется в `capturedAtSource`;
- записывает разрешение, модель камеры и запись в журнал `image_audit`.

Файлы отдаются только по токену или по подписанной ссылке HMAC-SHA256 со сроком жизни `SIGNED_URL_TTL_SECONDS` (900 с). При каждом чтении и перед анализом контрольная сумма сверяется с сохранённой; при расхождении файл не отдаётся (409) и не анализируется.

**Загрузка к конкретному растению:**
1. Вкладка **Растения** → раскройте карточку растения
2. Нажмите **+ Добавить фото**
3. Выберите папку и загрузите файлы — они привяжутся к этому растению

### Запуск фенотипирования

1. Откройте эксперимент → кнопка **Запустить**
2. **Шаг 1**: выберите фенотипическое решение (например, «Plant Height Measurement»)
   - Каждое решение показывает CropOntology переменные, которые оно измеряет
3. **Шаг 2**: выберите папку с изображениями для анализа
4. Нажмите **Запустить анализ**
5. Результаты появятся на вкладке **Результаты**

### Просмотр результатов

Вкладка **Результаты** показывает все запуски анализа в виде раскрывающихся карточек:

- **Заголовок**: название решения, статус (✅ завершён / ❌ ошибка / ⏳ в процессе), папка, кол-во изображений, CO ID
- **Раскрытие**: таблица с результатами по каждому изображению (файл, растение, переменная, значение в см, CO ID)
- **Статистика**: два признака (высота растения CO_321:0000020, площадь проекции листовой поверхности CO_321:0000080) — среднее ± SD, CV, 95% доверительный интервал по группам обработки, t-тест Уэлча относительно контроля, динамика по датам съёмки, скорость роста каждого растения (AGR, RGR) и корреляция признаков

### Экспорт

- В эксперименте: кнопки **XLSX**, **PDF**, **CSV** и **ZIP**
- Раздел **Экспорт**: несколько экспериментов, выбор переменных и периода съёмки, форматы XLSX, PDF, CSV и JSON (BrAPI)

| Формат | Содержимое |
|--------|-----------|
| XLSX | листы «Результаты», «Статистика», «Динамика» (с графиками), «Рост растений», «Сведения» |
| PDF | отчёт: сведения об эксперименте, статистика и сравнение групп, графики динамики, таблица измерений, примеры аннотированных снимков |
| CSV | UTF-8 с BOM, открывается в Excel без перекодировки |
| ZIP | исходные снимки, аннотированные снимки, CSV, XLSX, PDF и `manifest.json` с SHA-256 каждого файла |

### Управление переменными CropOntology

Раздел **Переменные** — каталог переменных наблюдения по стандарту CropOntology:

- Каждая переменная = Признак (Trait) + Метод (Method) + Шкала (Scale)
- Поиск по названию, признаку или CO ID
- Создание новой переменной через 4-шаговый мастер
- Удаление переменных кнопкой 🗑

### Фенотипические решения

Раздел **Фенотипические решения** — реестр алгоритмов анализа:

- Каждое решение содержит: Dockerfile, Kubernetes Job манифест, выходные CO переменные, калибровочные параметры
- Администраторы могут создавать и собирать решения через веб-интерфейс
- Исследователи видят доступные решения при запуске анализа

---

## Структура проекта

```
phenoplant/
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI приложение
│   │   ├── auth.py           # JWT + Keycloak валидация
│   │   ├── analyze.py        # OpenCV алгоритм (Plant Height)
│   │   ├── config.py         # Конфигурация
│   │   ├── database.py       # MongoDB подключение
│   │   ├── models/
│   │   │   └── schemas.py    # Pydantic модели
│   │   └── routers/
│   │       ├── auth.py       # /api/auth/*
│   │       ├── programs.py   # /api/programs
│   │       ├── trials.py     # /api/trials
│   │       ├── studies.py    # /api/studies + анализ
│   │       ├── variables.py  # /api/variables (с population)
│   │       ├── images.py     # /api/images (GridFS)
│   │       ├── admin.py      # /api/admin/solutions
│   │       └── ...
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── views/            # 13 экранов
│   │   ├── composables/      # useAuth, useApi, useProgram
│   │   ├── components/       # AppSidebar, AppLayout
│   │   ├── router/           # Vue Router
│   │   └── types/            # TypeScript типы
│   ├── package.json
│   └── Dockerfile
└── k8s/
    ├── mongodb.yaml          # StatefulSet + PVC
    ├── backend.yaml          # Deployment (2 реплики)
    ├── frontend.yaml         # Deployment + nginx
    ├── keycloak.yaml         # Deployment
    └── ingress.yaml          # nginx Ingress rules
```

## API Endpoints

| Метод | Путь | Описание |
|-------|------|----------|
| POST | /api/auth/login | Вход (email + password → JWT) |
| POST | /api/auth/register | Регистрация |
| POST | /api/auth/refresh | Обновление токена |
| GET/POST/DELETE | /api/programs | Программы CRUD |
| GET/POST/DELETE | /api/trials | Испытания CRUD |
| GET/POST/DELETE | /api/studies | Эксперименты CRUD |
| GET | /api/studies/{id} | Детали эксперимента |
| GET | /api/studies/{id}/observation-units | Растения эксперимента |
| POST | /api/studies/{id}/run-analysis | Запуск анализа |
| GET | /api/studies/{id}/analysis-runs | Результаты анализов |
| GET/POST/DELETE | /api/variables | Переменные (с population trait/method/scale) |
| GET | /api/studies/{id}/trait-summary | Статистика по высоте и площади листьев |
| GET | /api/studies/{id}/export?format=xlsx\|pdf\|csv\|json | Экспорт результатов эксперимента |
| GET | /api/studies/{id}/export-zip | Архив со снимками, отчётами и manifest.json |
| POST | /api/export | Экспорт по нескольким экспериментам с фильтрами |
| POST | /api/images/upload | Загрузка одного снимка |
| POST | /api/images/upload-batch | Массовая загрузка фото (поле `capturedAt` на каждый файл) |
| POST | /api/images/upload-plant | Загрузка фото к растению |
| GET | /api/images/by-study/{id} | Изображения эксперимента (с подписанными ссылками) |
| POST | /api/images/signed-urls | Подписанные ссылки на снимки |
| GET | /api/images/file/{id} | Файл снимка (токен или `exp`+`sig`) |
| GET | /api/images/timeline/{study_id} | Снимки по датам съёмки |
| GET | /api/images/integrity/{study_id} | Проверка контрольных сумм всех снимков |
| GET | /api/images/{id}/environment | Показания датчиков камеры в окне ±30 мин от съёмки |
| DELETE | /api/images/{id} | Удаление снимка (admin, researcher) |
| GET/POST | /api/sensor-readings | Показания датчиков климатической камеры |
| GET | /api/admin/solutions | Список решений |
| GET | /api/dashboard | Статистика |

## Тесты

```bash
cd backend
pip install -r requirements.txt -r requirements-dev.txt
pytest
```

Тесты используют `mongomock-motor` и хранилище в памяти, MongoDB и Keycloak не нужны.

## Лицензия

MIT

---

## Документация

- [README.md](README.md) — быстрый старт и руководство пользователя
- [SOLUTIONS.md](SOLUTIONS.md) — создание фенотипических решений (Dockerfile, манифест, outputVariables)
- [site/README.md](site/README.md) — сайт стартап-проекта и его публикация на GitHub Pages
