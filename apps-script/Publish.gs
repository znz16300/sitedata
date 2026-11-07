/**
 * Кнопка «🌐 Сайт → Опублікувати зараз» у Google Таблиці.
 *
 * Запускає оновлення сайту на GitHub одразу, не чекаючи розкладу (кожні 30 хв).
 * Встановлюється окремо в кожну таблицю, з якої беруться дані (новини, сторінки, документи…).
 * Покрокова інструкція — README.md → «Кнопка в Google Таблиці».
 */

// ======================= НАЛАШТУВАННЯ =======================
const GITHUB_REPO = 'znz16300/sitedata';   // власник/репозиторій
const WORKFLOW_FILE = 'publish.yml';       // .github/workflows/publish.yml
const BRANCH = 'main';
// Яку таблицю оновлювати (поле name у config.json). Порожньо — усі таблиці.
// Для таблиці новин: 'news'; для сторінок: 'pages'; документів: 'documents'…
const ONLY_TABLES = '';
// ============================================================

const TOKEN_KEY = 'GITHUB_TOKEN';

function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu('🌐 Сайт')
    .addItem('Опублікувати зараз', 'publishNow')
    .addItem('Переглянути журнал публікацій', 'openRuns')
    .addSeparator()
    .addItem('Налаштувати токен GitHub…', 'setToken')
    .addItem('Публікувати автоматично після кожної відповіді форми', 'installFormTrigger')
    .addToUi();
}

/** Пункт меню: запустити оновлення зараз. */
function publishNow() {
  const res = dispatch_('кнопка: ' + Session.getActiveUser().getEmail());
  const ss = SpreadsheetApp.getActive();
  if (res.ok) {
    ss.toast('Оновлення запущено. Сайт зміниться за 1–3 хвилини.', '🌐 Сайт', 8);
  } else {
    SpreadsheetApp.getUi().alert('Не вдалося запустити оновлення:\n\n' + res.message);
  }
}

/** Пункт меню: відкрити сторінку запусків на GitHub. */
function openRuns() {
  const url = 'https://github.com/' + GITHUB_REPO + '/actions/workflows/' + WORKFLOW_FILE;
  const html = HtmlService.createHtmlOutput(
    '<p>Журнал оновлень сайту:</p><p><a href="' + url + '" target="_blank">' + url + '</a></p>'
  ).setWidth(460).setHeight(120);
  SpreadsheetApp.getUi().showModalDialog(html, 'Журнал публікацій');
}

/** Пункт меню: зберегти токен (у властивостях скрипта, не в коді). */
function setToken() {
  const ui = SpreadsheetApp.getUi();
  const r = ui.prompt(
    'Токен GitHub',
    'Вставте fine-grained токен з доступом лише до репозиторію ' + GITHUB_REPO +
      ' і правом «Actions: Read and write».',
    ui.ButtonSet.OK_CANCEL
  );
  if (r.getSelectedButton() !== ui.Button.OK) return;
  const token = r.getResponseText().trim();
  if (!token) return;
  PropertiesService.getScriptProperties().setProperty(TOKEN_KEY, token);
  const test = dispatch_('перевірка токена');
  ui.alert(test.ok ? '✅ Токен збережено, тестове оновлення запущено.' : '⚠️ Токен збережено, але запуск не вдався:\n\n' + test.message);
}

/** Пункт меню: автопублікація після кожної відповіді Google-форми. */
function installFormTrigger() {
  const ss = SpreadsheetApp.getActive();
  ScriptApp.getProjectTriggers()
    .filter(function (t) { return t.getHandlerFunction() === 'onFormSubmitPublish'; })
    .forEach(function (t) { ScriptApp.deleteTrigger(t); });
  ScriptApp.newTrigger('onFormSubmitPublish').forSpreadsheet(ss).onFormSubmit().create();
  ss.toast('Готово: після кожної відповіді форми сайт оновлюватиметься автоматично.', '🌐 Сайт', 8);
}

/** Тригер «надіслано форму». Кілька відповідей підряд → один запуск (пауза 2 хв). */
function onFormSubmitPublish() {
  const cache = CacheService.getScriptCache();
  if (cache.get('recently-dispatched')) return;
  cache.put('recently-dispatched', '1', 120);
  dispatch_('нова відповідь форми');
}

function dispatch_(reason) {
  const token = PropertiesService.getScriptProperties().getProperty(TOKEN_KEY);
  if (!token) {
    return { ok: false, message: 'Токен не налаштовано. Меню «🌐 Сайт» → «Налаштувати токен GitHub…».' };
  }
  const url = 'https://api.github.com/repos/' + GITHUB_REPO + '/actions/workflows/' + WORKFLOW_FILE + '/dispatches';
  const resp = UrlFetchApp.fetch(url, {
    method: 'post',
    contentType: 'application/json',
    headers: {
      Authorization: 'Bearer ' + token,
      Accept: 'application/vnd.github+json',
      'X-GitHub-Api-Version': '2022-11-28',
    },
    payload: JSON.stringify({
      ref: BRANCH,
      inputs: { only: ONLY_TABLES, reason: (SpreadsheetApp.getActive().getName() + ' — ' + reason).slice(0, 200) },
    }),
    muteHttpExceptions: true,
  });
  const code = resp.getResponseCode();
  if (code === 204) return { ok: true };
  const hints = {
    401: 'Токен недійсний або прострочений — створіть новий.',
    403: 'У токена немає права «Actions: Read and write» для цього репозиторію.',
    404: 'Не знайдено репозиторій/workflow або токен не має до нього доступу.',
    422: 'Невірна гілка (BRANCH) або workflow вимкнено.',
  };
  return { ok: false, message: 'HTTP ' + code + '. ' + (hints[code] || resp.getContentText().slice(0, 300)) };
}
