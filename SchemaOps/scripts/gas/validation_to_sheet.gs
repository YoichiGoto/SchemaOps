// Copy rows from a local CSV (exported elsewhere) into the Google Sheet Validation_Checklist.
// For demo: paste parsed rows passed via a manual input (later can be replaced by Drive file read).
const VC_SHEET = 'Validation_Checklist';

function upsertValidationRows(rows) {
  const ss = SpreadsheetApp.openById(SPREADSHEET_ID);
  const sh = ss.getSheetByName(VC_SHEET);
  const last = sh.getLastRow();
  sh.getRange(last+1,1,rows.length,rows[0].length).setValues(rows);
}

// Example payload format matches columns:
// ['SKU','attributeId','checkType','passFail','failReason','autoFixRule','reviewer','checkedAt']
function demoPushValidation() {
  const now = Utilities.formatDate(new Date(), Session.getScriptTimeZone(), 'yyyy-MM-dd');
  const rows = [
    ['SKU-TEST','title','required','PASS','', '', 'ops', now],
    ['SKU-TEST','gtin','length','FAIL','too short', 'padOrValidateGTIN', 'ops', now]
  ];
  upsertValidationRows(rows);
}
