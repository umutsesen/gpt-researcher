const WebSocket = require('ws');

const ws = new WebSocket('ws://127.0.0.1:8000/ws');

// === Updated test data with correct doc_path ===
const startPayload = {
  task: "Yenilenebilir Enerji Teknolojileri ve Geleceği",
  report_type: "research_report",
  report_source: "local",
  tone: "Objective",
  source_urls: [],
  agent: "auto_agent",
  query_domains: [],
  language: "tr",
  doc_path: "C:/Users/Lenovo/Desktop/Easy/easyNew/newgpt/gpt-researcher/gpt_researcher/my-docs"
};

const secondMessage = {
  query: startPayload.task,
  sources: [],
  context: {},
  report: ""
};

// === connection lifecycle ===
ws.on('open', () => {
  console.log('[OPEN] WebSocket connected');

  // First message (the "start" command)
  ws.send(`start ${JSON.stringify(startPayload)}`);
  console.log('[SEND] start payload sent');

  // Second message (detailed query)
  ws.send(JSON.stringify(secondMessage));
  console.log('[SEND] second message sent');
});

ws.on('message', (data) => {
  let parsed;
  try {
    parsed = JSON.parse(data.toString());
  } catch (e) {
    console.log('[RECEIVE] Non-JSON message:', data.toString());
    return;
  }

  if (parsed.type === 'logs') {
    console.log(`[LOG] ${parsed.content}`);
  } else if (parsed.type === 'report') {
    console.log(`[REPORT CHUNK] ${parsed.output?.substring(0, 100)}...`);
  } else {
    console.log('[RECEIVE]', parsed);
  }

  if (parsed.type === 'logs' && parsed.content === 'report_written') {
    console.log('[CLOSE] Report complete. Closing connection.');
    ws.close();
  }
});

ws.on('close', () => {
  console.log('[CLOSED] WebSocket closed.');
});

ws.on('error', (err) => {
  console.error('[ERROR]', err);
});

console.log('Testing doc_path integration...');
console.log('Make sure you have files in:', startPayload.doc_path);
