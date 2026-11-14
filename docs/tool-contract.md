# Контракт процессора (Tool)

Процессор выполняет одну операцию над документом. Все процессоры работают через один контракт,
поэтому Dispatcher не знает конкретных классов, а новый процессор добавляется регистрацией
в `ProcessorRegistry` без правки Dispatcher. Место процессоров в системе — [architecture.md](architecture.md).

## Интерфейс

```python
from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class Document:
    id: str             # UUID документа
    path: str           # путь к файлу в DocumentStore
    format: str         # "pdf" | "docx" | "txt" — уже проверен DocumentValidator
    size_bytes: int


@dataclass(frozen=True)
class ProcessingResult:
    ok: bool
    data: dict[str, Any] = field(default_factory=dict)   # результат при ok=True
    error_code: str | None = None                        # код ошибки при ok=False
    error_message: str | None = None


class InvalidParams(Exception):
    """Неверные параметры операции. field — имя поля, например 'params.target_lang'."""

    def __init__(self, field: str, message: str) -> None:
        super().__init__(message)
        self.field = field
        self.message = message


class Processor(Protocol):
    name: str  # имя операции: "extract_text", "stats", "convert", "translate"

    def validate_params(self, params: dict[str, Any]) -> None:
        """Проверяет параметры. Неверные — InvalidParams с именем поля. Ничего не возвращает."""

    def run(self, document: Document, params: dict[str, Any]) -> ProcessingResult:
        """Выполняет операцию. Ожидаемая ошибка — ProcessingResult(ok=False, ...)."""
```

## Что процессор получает и что возвращает

| | Описание |
|---|---|
| **Вход `run`** | `Document` — уже проверенный документ (формат и размер проверил `DocumentValidator`); `params` — параметры, уже прошедшие `validate_params` |
| **Выход `run` при успехе** | `ProcessingResult(ok=True, data={...})` — данные результата; Dispatcher переводит Job в `processed` и сохраняет `data` в `result` |
| **Выход `run` при ожидаемой ошибке** | `ProcessingResult(ok=False, error_code="...", error_message="...")` — Dispatcher переводит Job в `failed`, код попадает в `error.code` |
| **Исключение из `run`** | Неожиданная ошибка (баг, сбой библиотеки). Dispatcher ловит любое исключение и переводит Job в `failed` с `error.code = "internal_error"`; сервис продолжает работать |

## Кто проверяет параметры

**Параметры проверяет процессор** — методом `validate_params`. Вызывает его **HTTP API при `POST /jobs`**,
до создания задания: процессор знает свои параметры лучше всех, а клиент получает ошибку сразу,
синхронно, а не через упавшее задание.

- Неверные параметры → `InvalidParams(field, message)` → API отвечает `400 invalid_params`,
  `details.field = field`; задание не создаётся.
- Неизвестная операция → `ProcessorRegistry` бросает `UnknownOperation` → `400 unknown_operation`.
- `run` может рассчитывать, что параметры уже проверены, и повторно их не валидирует.

## Правила для всех процессоров

- Не импортируют веб-фреймворк и драйвер БД; работают только с `Document`, `params` и своими библиотеками.
- Не меняют состояние Job — это делает только Dispatcher через правила Job.
- Не пишут в хранилище задания; файл результата (для `convert`) сохраняют через переданный им `DocumentStore`.
- Обращаются к внешним сервисам только через адаптер (сейчас — `TranslationClient`).
- Должны завершаться за ограниченное время: долгие внешние вызовы — с таймаутом в адаптере.

## Ошибки процессоров

| `error_code` | Кто возвращает | Когда |
|---|---|---|
| `parse_error` | `TextExtractor`, `StatsProcessor`, `FormatConverter` | Сигнатура файла верная, но содержимое не читается (файл обрезан) |
| `text_too_long` | `Translator` | Текст длиннее 50 000 символов |
| `translation_unavailable` | `Translator` | Сервис перевода не ответил или вернул 5xx после 3 попыток |
| `translation_rejected` | `Translator` | Сервис перевода отклонил запрос ответом 4xx (кроме 429), например `400` из-за неподдерживаемой пары языков; повтор не делается, HTTP-статус — в `error.message` |
| `translation_bad_response` | `Translator` | Сервис перевода вернул не JSON или ответ без поля с переводом; повтор не делается |
| `unsupported_conversion` | `FormatConverter` | Конвертации из формата документа в запрошенный формат нет (PDF → PDF, TXT → TXT) |
| `internal_error` | Dispatcher | Процессор выбросил исключение |

`unsupported_format` и `corrupted_file` (неверная сигнатура) процессоры не возвращают: такие документы
отклоняет `DocumentValidator` ещё до выполнения (Job → `rejected`).

## Процессоры через этот контракт

### TextExtractor

| | |
|---|---|
| `name` | `extract_text` |
| Параметры | Нет. Любой непустой `params` → `InvalidParams("params", "extract_text takes no params")` |
| Что делает | Извлекает текст: PDF — pypdf, DOCX — python-docx, TXT — чтение в UTF-8 |
| Успех | `{"text": "..."}`; для документа без текста (например, PDF из картинок) — `{"text": ""}`, это не ошибка |
| Ошибки | `parse_error` — файл не читается библиотекой |

### StatsProcessor

| | |
|---|---|
| `name` | `stats` |
| Параметры | Нет. Любой непустой `params` → `InvalidParams("params", "stats takes no params")` |
| Что делает | Получает текст тем же способом, что `TextExtractor`, и считает слова, символы, абзацы и 10 самых частых слов |
| Успех | `{"words": 1520, "chars": 9874, "paragraphs": 42, "top_words": [["документ", 31], ...]}`; пустой документ — нули и пустой `top_words` |
| Ошибки | `parse_error` — файл не читается |

### Translator

| | |
|---|---|
| `name` | `translate` |
| Параметры | `target_lang` — обязателен, двухбуквенный код (`en`, `ru`, …); `source_lang` — необязателен, если не передан — определяется автоматически, если передан — проверяется по тем же правилам. Нет `target_lang` → `InvalidParams("params.target_lang", "target_lang is required")`; `target_lang` или переданный `source_lang` — не два латинских символа → `InvalidParams("params.target_lang" или "params.source_lang", "... must be a two-letter language code")` |
| Что делает | Извлекает текст и отправляет его в `TranslationClient` |
| Успех | `{"text": "...", "source_lang": "ru", "target_lang": "en"}` |
| Ошибки | `text_too_long`, `translation_unavailable`, `translation_rejected`, `translation_bad_response` |

### FormatConverter

| | |
|---|---|
| `name` | `convert` |
| Параметры | `target_format` — обязателен, `pdf` или `txt`; иначе `InvalidParams("params.target_format", ...)` |
| Что делает | Поддерживаемые пары: DOCX → PDF, TXT → PDF, PDF → TXT, DOCX → TXT. Сохраняет файл результата в `DocumentStore` |
| Успех | `{"format": "pdf", "size_bytes": 48211}`; файл — `GET /jobs/{id}/result` |
| Ошибки | `parse_error`; `unsupported_conversion` — пары нет в списке (PDF → PDF, TXT → TXT) |

Неподдерживаемая пара не отклоняется при `POST /jobs`: `validate_params` получает только `params`,
а формат документа становится известен после проверки `DocumentValidator`. Поэтому задание создаётся
и переходит в `failed` с `error.code = "unsupported_conversion"`, а в `error.message` — формат документа
и запрошенный формат.

## Адаптер внешнего сервиса: TranslationClient

`Translator` не знает протокола LibreTranslate — он вызывает `TranslationClient.translate(text, source_lang, target_lang) -> str`.
Адаптер:
- ставит таймаут 10 с на запрос;
- повторяет запрос до 3 раз с паузой только при таймауте, ответе 5xx и ответе `429 Too Many Requests`
  (для `429` пауза — из заголовка `Retry-After`, но не больше 10 с);
- при остальных ответах 4xx сразу бросает `TranslationRejected` без повторов — повтор того же запроса даст тот же отказ;
- при ответе не в JSON или без поля с переводом сразу бросает `TranslationBadResponse` без повторов;
- после исчерпания попыток бросает `TranslationUnavailable`;
- в тестах заменяется fake-сервером с управляемыми ответами (успех, задержка, 500, мусор).

`Translator` превращает эти исключения в `ProcessingResult(ok=False, ...)` с кодами из таблицы ошибок.
Если LibreTranslate переименует поле ответа, меняется только `TranslationClient` и его тесты.
