const READING_HEADERS = [
  'event_id', 'recorded_at', 'recorded_at_th', 'device_id', 'soil_moisture_percent',
  'soil_temperature_c', 'soil_ec', 'soil_ph', 'soil_n', 'soil_p', 'soil_k',
  'air_temperature_c', 'humidity_percent', 'outdoor_temperature_c',
  'outdoor_humidity_percent', 'pressure_hpa', 'wind_avg', 'wind_gust',
  'rain_1h_mm', 'rain_24h_mm', 'rain_rate_mm_h', 'uv_index', 'dew_point_c',
  'feels_like_c', 'heat_index_c', 'light_lux'
];

function doPost(e) {
  const props = PropertiesService.getScriptProperties();
  if (!e || e.parameter.key !== props.getProperty('DEVICE_INGEST_KEY')) {
    return jsonResponse_({ ok: false, error: 'unauthorized' });
  }

  let data;
  try {
    data = JSON.parse(e.postData.contents);
  } catch (err) {
    return jsonResponse_({ ok: false, error: 'invalid_json' });
  }

  const lock = LockService.getScriptLock();
  lock.waitLock(10000);
  try {
    const book = SpreadsheetApp.openById(props.getProperty('SPREADSHEET_ID'));
    appendReading_(book, data);
    upsertNdvi_(book, data);
    upsertForecast_(book, data);
    upsertHourlyForecast_(book, data);
  } finally {
    lock.releaseLock();
  }

  return jsonResponse_({ ok: true, event_id: data.event_id || '' });
}

// Run this once from the Apps Script editor to repair existing shifted rows
// immediately. New POST requests also run the same repair automatically.
function repairReadingsSheet() {
  const props = PropertiesService.getScriptProperties();
  const book = SpreadsheetApp.openById(props.getProperty('SPREADSHEET_ID'));
  const sheet = getSheet_(book, 'readings_15min', READING_HEADERS);
  ensureReadingHeaders_(sheet);
}

function appendReading_(book, data) {
  const sheet = getSheet_(book, 'readings_15min', READING_HEADERS);
  ensureReadingHeaders_(sheet);
  const eventId = data.event_id || `${data.device_id || 'unknown'}:${data.recorded_at || new Date().toISOString()}`;
  if (sheet.getLastRow() > 1 && sheet.getRange(2, 1, sheet.getLastRow() - 1, 1)
      .createTextFinder(eventId).matchEntireCell(true).findNext()) return;

  const s = data.soil || {};
  const w = data.weather || {};
  const recordedAt = data.recorded_at || new Date().toISOString();
  sheet.appendRow([
    eventId, recordedAt, bangkokTime_(recordedAt), data.device_id || '',
    value_(s.moisture_percent), value_(s.temperature_c), value_(s.ec), value_(s.ph),
    value_(s.n), value_(s.p), value_(s.k),
    value_(w.air_temperature_c), value_(w.humidity_percent),
    value_(w.outdoor_temperature_c), value_(w.outdoor_humidity_percent),
    value_(w.pressure_hpa), value_(w.wind_avg), value_(w.wind_gust),
    value_(w.rain_1h_mm), value_(w.rain_24h_mm), value_(w.rain_rate_mm_h),
    value_(w.uv_index), value_(w.dew_point_c), value_(w.feels_like_c),
    value_(w.heat_index_c), value_(w.light_lux)
  ]);
}

function upsertNdvi_(book, data) {
  const n = data.ndvi || {};
  if (!n.valid || !n.captured_epoch) return;
  const headers = ['key', 'captured_at', 'mean', 'min', 'max', 'median', 'cloud_coverage', 'source', 'received_at'];
  const sheet = getSheet_(book, 'ndvi_daily', headers);
  const key = `${data.polygon_id || 'farm-main'}:${n.captured_epoch}`;
  upsertRow_(sheet, key, [key, new Date(n.captured_epoch * 1000), value_(n.mean), value_(n.min),
    value_(n.max), value_(n.median), value_(n.cloud_coverage), n.source || '', data.recorded_at || new Date()]);
}

function upsertForecast_(book, data) {
  if (!Array.isArray(data.forecast_7day)) return;
  const headers = ['key', 'issued_date', 'forecast_date', 'temp_max_c', 'temp_min_c',
    'humidity_percent', 'rain_mm', 'condition_code', 'received_at', 'source',
    'pressure_hpa', 'wind_speed_ms', 'wind_direction_deg', 'cloud_low_percent',
    'cloud_mid_percent', 'cloud_high_percent', 'shortwave'];
  const sheet = getSheet_(book, 'forecast_daily', headers);
  ensureHeaders_(sheet, headers);
  const issued = String(data.recorded_at || new Date().toISOString()).slice(0, 10);
  data.forecast_7day.forEach(day => {
    if (!day.date) return;
    const key = `${data.location_id || 'farm-main'}:${issued}:${day.date}`;
    upsertRow_(sheet, key, [key, issued, day.date, value_(day.temp_max_c),
      value_(day.temp_min_c), value_(day.humidity_percent), value_(day.rain_mm),
      value_(day.cond), data.recorded_at || new Date(), data.forecast_source || '',
      value_(day.pressure_hpa), value_(day.wind_speed_ms), value_(day.wind_direction_deg),
      value_(day.cloud_low_percent), value_(day.cloud_mid_percent),
      value_(day.cloud_high_percent), value_(day.shortwave)]);
  });
}

function upsertHourlyForecast_(book, data) {
  if (!Array.isArray(data.forecast_hourly)) return;
  const headers = ['key', 'issued_at', 'forecast_time', 'temperature_c',
    'humidity_percent', 'pressure_hpa', 'rain_mm', 'wind_speed_ms',
    'wind_direction_deg', 'cloud_low_percent', 'cloud_mid_percent',
    'cloud_high_percent', 'condition_code', 'source', 'received_at'];
  const sheet = getSheet_(book, 'forecast_hourly', headers);
  const issued = String(data.recorded_at || new Date().toISOString());
  data.forecast_hourly.forEach(hour => {
    if (!hour.time) return;
    const key = `${data.location_id || 'farm-main'}:${issued}:${hour.time}`;
    upsertRow_(sheet, key, [key, issued, hour.time, value_(hour.temperature_c),
      value_(hour.humidity_percent), value_(hour.pressure_hpa), value_(hour.rain_mm),
      value_(hour.wind_speed_ms), value_(hour.wind_direction_deg),
      value_(hour.cloud_low_percent), value_(hour.cloud_mid_percent),
      value_(hour.cloud_high_percent), value_(hour.cond),
      data.hourly_forecast_source || '', data.recorded_at || new Date()]);
  });
}

function upsertRow_(sheet, key, row) {
  let found = null;
  if (sheet.getLastRow() > 1) {
    found = sheet.getRange(2, 1, sheet.getLastRow() - 1, 1)
      .createTextFinder(key).matchEntireCell(true).findNext();
  }
  if (found) sheet.getRange(found.getRow(), 1, 1, row.length).setValues([row]);
  else sheet.appendRow(row);
}

function getSheet_(book, name, headers) {
  let sheet = book.getSheetByName(name);
  if (!sheet) sheet = book.insertSheet(name);
  if (sheet.getLastRow() === 0) sheet.appendRow(headers);
  return sheet;
}

function ensureReadingHeaders_(sheet) {
  let lastColumn = Math.max(sheet.getLastColumn(), 1);
  let headers = sheet.getRange(1, 1, 1, lastColumn).getValues()[0];

  // Migrate an existing sheet safely: delete the obsolete LoRa column so all
  // weather columns and historical values shift left together.
  const loraIndex = headers.indexOf('lora_rssi');
  if (loraIndex !== -1) {
    sheet.deleteColumn(loraIndex + 1);
    lastColumn = Math.max(sheet.getLastColumn(), 1);
    headers = sheet.getRange(1, 1, 1, lastColumn).getValues()[0];
  }

  if (headers[2] !== 'recorded_at_th') {
    sheet.insertColumnAfter(2);
    const rowCount = sheet.getLastRow() - 1;
    if (rowCount > 0) {
      const utcValues = sheet.getRange(2, 2, rowCount, 1).getValues();
      const localValues = utcValues.map(row => [row[0] ? bangkokTime_(row[0]) : '']);
      sheet.getRange(2, 3, rowCount, 1).setValues(localValues);
    }
  }

  repairLegacyLoraGap_(sheet);
  sheet.getRange(1, 1, 1, READING_HEADERS.length).setValues([READING_HEADERS]);
  sheet.setFrozenRows(1);
}

function repairLegacyLoraGap_(sheet) {
  const rowCount = sheet.getLastRow() - 1;
  const legacyLastColumn = READING_HEADERS.length + 1; // AA: old light_lux
  if (rowCount < 1 || sheet.getLastColumn() < legacyLastColumn) return;

  // Old deployed code still wrote a blank lora_rssi at L, putting weather in
  // M:AA. Only repair rows that have the blank gap and a value in AA.
  const firstWeatherColumn = 12; // L
  const width = legacyLastColumn - firstWeatherColumn + 1; // L:AA
  const range = sheet.getRange(2, firstWeatherColumn, rowCount, width);
  const rows = range.getValues();
  let changed = false;

  rows.forEach(row => {
    if (row[0] === '' && row[width - 1] !== '') {
      for (let column = 0; column < width - 1; column++) {
        row[column] = row[column + 1];
      }
      row[width - 1] = '';
      changed = true;
    }
  });

  if (changed) range.setValues(rows);
}

function ensureTrailingHeader_(sheet, header) {
  const lastColumn = Math.max(sheet.getLastColumn(), 1);
  const headers = sheet.getRange(1, 1, 1, lastColumn).getValues()[0];
  if (headers.indexOf(header) !== -1) return;
  sheet.getRange(1, lastColumn + 1).setValue(header);
}

function ensureHeaders_(sheet, headers) {
  const current = sheet.getRange(1, 1, 1, Math.max(sheet.getLastColumn(), 1)).getValues()[0];
  headers.forEach(header => {
    if (current.indexOf(header) === -1) {
      current.push(header);
      sheet.getRange(1, current.length).setValue(header);
    }
  });
}

function bangkokTime_(value) {
  const date = value instanceof Date ? value : new Date(value);
  if (isNaN(date.getTime())) return '';
  return Utilities.formatDate(date, 'Asia/Bangkok', 'yyyy-MM-dd HH:mm:ss');
}

function value_(v) {
  return typeof v === 'number' && isFinite(v) ? v : '';
}

function jsonResponse_(value) {
  return ContentService.createTextOutput(JSON.stringify(value))
    .setMimeType(ContentService.MimeType.JSON);
}
