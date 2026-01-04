// Config
const SPREADSHEET_ID = '11gyHhfv0-jxOrFfHan7g2N9tWkm5kCYUF0kfVuAsQsY';
const SHEET_CHANGE_LOG = 'Change_Log';

// Lark App Bot (Webhook不可の場合)
const LARK_APP_ID = 'YOUR_APP_ID';
const LARK_APP_SECRET = 'YOUR_APP_SECRET';
const LARK_CHAT_ID = 'YOUR_CHAT_ID'; // 通知先グループ chat_id

function larkGetToken_() {
  const res = UrlFetchApp.fetch(
    'https://open.larksuite.com/open-apis/auth/v3/tenant_access_token/internal',
    { method: 'post', contentType: 'application/json',
      payload: JSON.stringify({ app_id: LARK_APP_ID, app_secret: LARK_APP_SECRET }) }
  );
  const json = JSON.parse(res.getContentText());
  if (!json.tenant_access_token) throw new Error('Lark token failed');
  return json.tenant_access_token;
}

function larkNotify(text) {
  const token = larkGetToken_();
  const url = 'https://open.larksuite.com/open-apis/im/v1/messages?receive_id_type=chat_id';
  const payload = { receive_id: LARK_CHAT_ID, msg_type: 'text', content: JSON.stringify({ text }) };
  UrlFetchApp.fetch(url, { method: 'post', contentType: 'application/json', headers: { Authorization: 'Bearer ' + token }, payload: JSON.stringify(payload) });
}

// サンプル: 1行追加
function appendChangeLogRowSample() {
  const ss = SpreadsheetApp.openById(SPREADSHEET_ID);
  const sh = ss.getSheetByName(SHEET_CHANGE_LOG);
  const now = Utilities.formatDate(new Date(), Session.getScriptTimeZone(), 'yyyy-MM-dd');
  const row = [now, 'mp', 'GMC Spec', 'Max length updated for title to 150', 'title', 'major', 120, '2025-10-31', 'new', 'ops', now, '', 'https://support.google.com/merchants/answer/7052112', ''];
  sh.appendRow(row);
}

// onEdit: Change_Logにcritical/newが入ったら通知
function onEdit(e) {
  try {
    const range = e.range; const sh = range.getSheet();
    if (sh.getName() !== SHEET_CHANGE_LOG) return;
    const row = sh.getRange(range.getRow(), 1, 1, sh.getLastColumn()).getValues()[0];
    const [date, target, name, changeSummary, impacted, severity, sla, eta, status, owner] = row;
    if ((severity + '').toLowerCase() === 'critical' && (status + '').toLowerCase() === 'new') {
      larkNotify(`[critical] ${name}: ${changeSummary} | ETA=${eta} | Owner=${owner}`);
    }
  } catch (err) {
    console.error(err);
  }
}

// 時間駆動: 未通知のcritical/majorをサンプリングして通知
function scanChangeLogAndNotify() {
  const ss = SpreadsheetApp.openById(SPREADSHEET_ID);
  const sh = ss.getSheetByName(SHEET_CHANGE_LOG);
  const data = sh.getDataRange().getValues();
  const header = data[0];
  const idx = (name) => header.indexOf(name);
  const notified = PropertiesService.getScriptProperties().getProperty('notified') || '{}';
  const seen = JSON.parse(notified);
  for (let i = 1; i < data.length; i++) {
    const r = data[i];
    const key = `${i}`;
    const sev = (r[idx('severity')] + '').toLowerCase();
    const status = (r[idx('status')] + '').toLowerCase();
    if ((sev === 'critical' || sev === 'major') && status === 'new' && !seen[key]) {
      const name = r[idx('name')];
      const summary = r[idx('changeSummary')];
      const eta = r[idx('ETA')];
      const owner = r[idx('owner')];
      larkNotify(`[${sev}] ${name}: ${summary} | ETA=${eta} | Owner=${owner}`);
      seen[key] = true;
    }
  }
  PropertiesService.getScriptProperties().setProperty('notified', JSON.stringify(seen));
}

// 初期セットアップ: 時間駆動トリガを毎時登録
function setupTriggers() {
  // 既存トリガ削除
  ScriptApp.getProjectTriggers().forEach(t => ScriptApp.deleteTrigger(t));
  ScriptApp.newTrigger('scanChangeLogAndNotify').timeBased().everyHours(1).create();
}
