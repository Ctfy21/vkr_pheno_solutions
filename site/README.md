# Сайт стартап-проекта PhenoPlant

Статическая страница без сборки: `index.html` и изображения в `img/`.

## Перед публикацией

1. Логотип Фонда содействия инновациям. Скачайте официальный логотип с fasie.ru (раздел «Фирменный стиль»), положите в `img/fasie-logo.png` и замените оба блока `<div class="fund-logo">…</div>` на
   `<div class="fund-logo"><img src="img/fasie-logo.png" alt="Фонд содействия инновациям"></div>`.
   Логотип и текст о поддержке Фонда должны оставаться на главной странице.
2. Контакты в разделе «Контакты» (помечены жёлтым): e-mail, телефон, Telegram, название и ИНН ООО.
3. При необходимости поправьте тарифы и состав команды.

## Публикация на GitHub Pages

1. В репозитории: Settings → Pages → Build and deployment → Source: **GitHub Actions**.
2. После слияния в `main` workflow `.github/workflows/pages.yml` опубликует сайт по адресу
   `https://ctfy21.github.io/vkr_pheno_solutions/`.
3. Свой домен: добавьте файл `site/CNAME` с именем домена и настройте DNS по инструкции GitHub Pages.

## Изображения

- `plant.webp` — реальная фотография сои с автоматическим замером высоты.
- `statistics.webp`, `upload.webp`, `annotated.webp`, `method.webp` — экраны платформы на тестовом наборе снимков.
