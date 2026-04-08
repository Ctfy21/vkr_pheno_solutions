# Фенотипические решения (Phenotyping Solutions)

Фенотипические решения — это контейнеризированные алгоритмы анализа изображений растений, которые можно добавлять в платформу через административную панель.

## Концепция

Каждое решение состоит из 4 компонентов:

1. **Dockerfile** — описывает сборку Docker-образа с алгоритмом
2. **Kubernetes Job манифест** — описывает запуск контейнера в кластере
3. **Выходные переменные (outputVariables)** — какие CO переменные алгоритм измеряет
4. **Конфигурация (config)** — калибровочные параметры алгоритма

---

## Создание нового решения

### Через административную панель (UI)

1. Войдите с ролью **admin**
2. Перейдите в **Фенотипические решения** → **Создать решение**
3. Заполните:
   - **Название**: например, «Plant Height Measurement»
   - **Версия**: например, «1.0.0»
   - **Описание**: что делает алгоритм
   - **Dockerfile**: содержимое Dockerfile (см. примеры ниже)
   - **Manifest**: YAML манифест Kubernetes Job (см. примеры ниже)
4. Нажмите **Создать**
5. Нажмите **Собрать** — система выполнит `docker build` и импортирует образ в MicroK8s

### Через API

```bash
curl -X POST http://<IP>/api/admin/solutions \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Plant Height Measurement",
    "version": "1.0.0",
    "description": "Измерение высоты растений по RGB-изображениям",
    "dockerfile": "<содержимое Dockerfile>",
    "manifest": "<содержимое YAML манифеста>"
  }'
```

После создания обновите решение с outputVariables:

```bash
# Через MongoDB напрямую или через скрипт
db.phenotyping_solutions.updateOne(
  { name: "Plant Height Measurement" },
  { $set: {
    outputVariables: [{
      coTermId: "CO_321:0000020",
      name: "Plant height",
      unit: "см",
      description: "Высота растения от основания до верхушки"
    }],
    config: {
      scale_px_per_cm: 0,
      method: "hsv_optimized_autoResearch_v2"
    }
  }}
)
```

---

## Dockerfile — как писать

### Требования

- Базовый образ с Python (или другим языком)
- Установленные зависимости алгоритма
- Точка входа (ENTRYPOINT) — скрипт обработки
- Принимает аргументы: путь к изображениям и выходной файл

### Пример: измерение высоты растений (OpenCV)

```dockerfile
FROM python:3.12-slim

# Установка системных зависимостей для OpenCV
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx libglib2.0-0 && \
    rm -rf /var/lib/apt/lists/*

# Установка Python-зависимостей
RUN pip install --no-cache-dir opencv-python-headless numpy

WORKDIR /app

# Копирование скрипта алгоритма
COPY measure_height.py /app/

# Точка входа
ENTRYPOINT ["python", "/app/measure_height.py"]

# Аргументы по умолчанию
CMD ["--input", "/data/images", "--output", "/data/results.json", "--scale", "10.0"]
```

### Пример: подсчёт колосьев пшеницы (YOLOv26)

```dockerfile
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx libglib2.0-0 libsm6 libxext6 && \
    rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir ultralytics torch torchvision opencv-python-headless

WORKDIR /app

# Копирование модели и скрипта
COPY wheat_ear_detector.py /app/
COPY weights/best.pt /app/weights/

ENTRYPOINT ["python", "/app/wheat_ear_detector.py"]
CMD ["--input", "/data/images", "--output", "/data/results.json", "--weights", "/app/weights/best.pt", "--conf", "0.25"]
```

### Пример: анализ листовой поверхности

```dockerfile
FROM python:3.12-slim

RUN pip install --no-cache-dir opencv-python-headless numpy scikit-image

WORKDIR /app
COPY leaf_area.py /app/

ENTRYPOINT ["python", "/app/leaf_area.py"]
CMD ["--input", "/data/images", "--output", "/data/results.json"]
```

### Правила написания Dockerfile

| Правило | Описание |
|---------|----------|
| Минимальный образ | Используйте `*-slim` варианты для экономии места |
| Фиксированные версии | Указывайте версии pip-пакетов (`opencv==4.9.0.80`) |
| Без кэша pip | `--no-cache-dir` уменьшает размер образа |
| ENTRYPOINT + CMD | ENTRYPOINT — скрипт, CMD — аргументы по умолчанию |
| Нет секретов | Не включайте токены, пароли или API-ключи в образ |

---

## Kubernetes Job манифест — как писать

### Структура манифеста

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: {{JOB_NAME}}                    # Подставляется платформой
  labels:
    app: phenoplant
    solution: my-solution-name
spec:
  backoffLimit: 2                        # Макс. число перезапусков при ошибке
  template:
    metadata:
      labels:
        app: phenoplant
        solution: my-solution-name
    spec:
      containers:
      - name: analyzer
        image: {{IMAGE_NAME}}            # Подставляется платформой
        args:
          - "--input"
          - "/data/images"
          - "--output"
          - "/data/results.json"
          - "--scale"
          - "10.0"
        resources:
          requests:                      # Минимальные гарантированные ресурсы
            memory: "128Mi"
            cpu: "250m"
          limits:                        # Максимально допустимые ресурсы
            memory: "512Mi"
            cpu: "1000m"
        volumeMounts:
        - name: data
          mountPath: /data
      restartPolicy: Never
      volumes:
      - name: data
        persistentVolumeClaim:
          claimName: phenoplant-data
```

### Переменные-заполнители (placeholders)

Платформа автоматически подставляет значения при создании Job:

| Placeholder | Описание |
|------------|----------|
| `{{JOB_NAME}}` | Уникальное имя Job (генерируется автоматически) |
| `{{IMAGE_NAME}}` | Имя Docker-образа решения (например, `phenoplant-solution-plant-height:1.0.0`) |
| `{{STUDY_ID}}` | ID эксперимента |

### Ресурсные ограничения — рекомендации

| Тип алгоритма | CPU requests | CPU limits | Memory requests | Memory limits |
|---------------|-------------|-----------|----------------|--------------|
| OpenCV (лёгкий) | 250m | 1000m | 128Mi | 512Mi |
| PyTorch CPU | 500m | 2000m | 512Mi | 2Gi |
| PyTorch GPU | 500m | 2000m | 1Gi | 4Gi |
| Тяжёлый ML | 1000m | 4000m | 2Gi | 8Gi |

> **250m** = четверть ядра CPU, **1000m** = 1 ядро, **Mi** = мебибайты, **Gi** = гибибайты

### Пример: минимальный манифест (без PVC)

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: {{JOB_NAME}}
spec:
  backoffLimit: 1
  template:
    spec:
      containers:
      - name: worker
        image: {{IMAGE_NAME}}
        resources:
          requests:
            memory: "256Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "2000m"
      restartPolicy: Never
```

### Пример: с GPU-ускорением

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: {{JOB_NAME}}
spec:
  backoffLimit: 2
  template:
    spec:
      containers:
      - name: gpu-worker
        image: {{IMAGE_NAME}}
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "4Gi"
            cpu: "2000m"
            nvidia.com/gpu: 1           # Требует аддон microk8s enable gpu
        volumeMounts:
        - name: data
          mountPath: /data
      restartPolicy: Never
      volumes:
      - name: data
        persistentVolumeClaim:
          claimName: phenoplant-data
```

---

## Выходные переменные (outputVariables)

Каждое решение должно декларировать, какие CropOntology переменные оно измеряет. Это обеспечивает автоматическую привязку результатов к семантическим стандартам.

### Формат

```json
{
  "outputVariables": [
    {
      "coTermId": "CO_321:0000020",
      "name": "Plant height",
      "unit": "см",
      "description": "Высота растения от основания до верхушки"
    }
  ]
}
```

### Распространённые переменные CropOntology

| CO ID | Название | Единица | Описание |
|-------|---------|---------|----------|
| CO_321:0000020 | Plant height | см | Высота растения (пшеница) |
| CO_321:0000050 | Spike length | мм | Длина колоса |
| CO_321:0000070 | Spike density | шт/м² | Плотность колосьев |
| CO_321:0000080 | Flag leaf area | см² | Площадь флагового листа |
| CO_321:0000090 | NDVI | — | Вегетационный индекс |
| CO_340:0000010 | Plant height | см | Высота растения (подсолнечник) |
| CO_340:0000020 | Head diameter | см | Диаметр корзинки |
| CO_340:0000060 | Leaf count | шт | Количество листьев |

---

## Конфигурация (config)

Объект `config` хранит калибровочные параметры, передаваемые алгоритму при запуске:

```json
{
  "config": {
    "scale_px_per_cm": 10.0,
    "method": "hsv_green_detection",
    "confidence_threshold": 0.25
  }
}
```

| Параметр | Описание |
|----------|----------|
| `scale_px_per_cm` | Пикселей на сантиметр (0 = автоопределение по линейке) |
| `method` | Метод анализа |
| `confidence_threshold` | Порог уверенности для детекции объектов |

---

## Полный пример: Plant Height Measurement

### 1. Dockerfile

```dockerfile
FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx libglib2.0-0 && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir opencv-python-headless numpy
WORKDIR /app
COPY measure_height.py /app/
ENTRYPOINT ["python", "/app/measure_height.py"]
CMD ["--input", "/data/images", "--output", "/data/results.json", "--scale", "10.0"]
```

### 2. Manifest

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: {{JOB_NAME}}
  labels:
    app: phenoplant
    solution: plant-height
spec:
  backoffLimit: 2
  template:
    metadata:
      labels:
        app: phenoplant
        solution: plant-height
    spec:
      containers:
      - name: plant-height
        image: {{IMAGE_NAME}}
        args: ["--input", "/data/images", "--output", "/data/results.json", "--scale", "10.0"]
        resources:
          requests:
            memory: "128Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "1000m"
        volumeMounts:
        - name: data
          mountPath: /data
      restartPolicy: Never
      volumes:
      - name: data
        persistentVolumeClaim:
          claimName: phenoplant-data
```

### 3. outputVariables

```json
[{
  "coTermId": "CO_321:0000020",
  "name": "Plant height",
  "unit": "см",
  "description": "Высота растения от основания до верхушки"
}]
```

### 4. config

```json
{
  "scale_px_per_cm": 0,
  "method": "hsv_optimized_autoResearch_v2"
}
```

`scale_px_per_cm: 0` означает автоматическое определение масштаба по линейке в кадре.
