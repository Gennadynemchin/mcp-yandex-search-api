# mcp-yandex-search-api

MCP-сервер для [Yandex Search API](https://aistudio.yandex.ru/docs/ru/search-api/operations/search-images.html).
Предоставляет инструмент `search_images` — поиск изображений по текстовому запросу в индексе Яндекс Картинок.

## Возможности

- Инструмент MCP [`search_images`](src/mcp_yandex_search_api/server.py:103) — поиск изображений по тексту.
- Все параметры Yandex Search API: `search_type`, `family_mode`, `fix_typo_mode`, `format`, `size`, `orientation`, `color`, `site`, `user_agent`, `page`, `docs_on_page`.
- Автоматический парсинг XML-ответа в JSON со ссылками на оригинал, превью и страницу-источник. Опционально — возврат сырого XML.
- Аутентификация по API-ключу сервисного аккаунта или IAM-токену.

## Требования

- Python ≥ 3.10
- [`uv`](https://docs.astral.sh/uv/) — менеджер пакетов.
- Сервисный аккаунт в Yandex Cloud с ролью `search-api.webSearch.user` и API-ключом со scope `yc.search-api.execute`. См. [документацию](https://aistudio.yandex.ru/docs/ru/search-api/operations/search-images.html#before-you-begin).

## Установка

```bash
git clone <repo-url> mcp-yandex-search-api
cd mcp-yandex-search-api
uv sync
```

## Переменные окружения

| Имя | Описание |
|---|---|
| `YANDEX_FOLDER_ID` | Идентификатор каталога Yandex Cloud. Обязательно. |
| `YANDEX_API_KEY` | API-ключ сервисного аккаунта (рекомендуется). |
| `YANDEX_IAM_TOKEN` | Альтернатива: IAM-токен. Используется, если не задан `YANDEX_API_KEY`. |

## Локальный запуск

```bash
export YANDEX_FOLDER_ID="b1g..."
export YANDEX_API_KEY="AQVN..."
uv run mcp-yandex-search-api
```

Сервер общается по stdio (стандарт MCP).

### MCP Inspector

Для отладки удобно использовать [MCP Inspector](https://github.com/modelcontextprotocol/inspector):

```bash
uv run mcp dev src/mcp_yandex_search_api/server.py
```

## Подключение к VS Code

В VS Code MCP-серверы настраиваются в файле [`.vscode/mcp.json`](.vscode/mcp.json:1) (для проекта) или в `settings.json` (глобально). Пример конфигурации см. в [`.vscode/mcp.json`](.vscode/mcp.json:1):

```json
{
  "servers": {
    "yandex-search-api": {
      "command": "uv",
      "args": [
        "--directory",
        "/абсолютный/путь/до/mcp-yandex-search-api",
        "run",
        "mcp-yandex-search-api"
      ],
      "env": {
        "YANDEX_FOLDER_ID": "b1g...",
        "YANDEX_API_KEY": "AQVN..."
      }
    }
  }
}
```

После сохранения файла откройте Command Palette → **MCP: List Servers** → запустите `yandex-search-api`. Инструмент `search_images` станет доступен в чате (например, в GitHub Copilot Chat в режиме Agent).

## Подключение к Cursor

Cursor читает конфигурацию из [`~/.cursor/mcp.json`](~/.cursor/mcp.json:1) (глобально) или из `.cursor/mcp.json` в корне проекта. Пример:

```json
{
  "mcpServers": {
    "yandex-search-api": {
      "command": "uv",
      "args": [
        "--directory",
        "/абсолютный/путь/до/mcp-yandex-search-api",
        "run",
        "mcp-yandex-search-api"
      ],
      "env": {
        "YANDEX_FOLDER_ID": "b1g...",
        "YANDEX_API_KEY": "AQVN..."
      }
    }
  }
}
```

Затем в Cursor: **Settings → MCP → Refresh**. Сервер появится в списке, инструмент `search_images` будет доступен ассистенту.

## Пример вызова инструмента

Параметры `search_images`:

```jsonc
{
  "query": "котики",
  "page": 0,
  "docs_on_page": 5,
  "search_type": "SEARCH_TYPE_RU",
  "family_mode": "FAMILY_MODE_MODERATE",
  "size": "IMAGE_SIZE_LARGE",
  "color": "IMAGE_COLOR_COLOR"
}
```

Ответ — JSON со списком результатов:

```jsonc
{
  "query": "котики",
  "page": 0,
  "results": [
    {
      "page_url": "https://example.com/article",
      "image_url": "https://example.com/img.jpg",
      "thumbnail_url": "https://avatars.mds.yandex.net/...",
      "title": "Заголовок страницы",
      "passages": ["..."]
    }
  ]
}
```

Передайте `"return_raw_xml": true`, чтобы получить исходный XML-ответ Yandex Search API.

## Допустимые значения параметров

См. [официальную документацию](https://aistudio.yandex.ru/docs/ru/search-api/operations/search-images.html#execute-request). Полный список значений также объявлен в типах [`server.py`](src/mcp_yandex_search_api/server.py:1).
