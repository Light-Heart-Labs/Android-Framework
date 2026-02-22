// Inject gateway auth token into Control UI so it auto-connects
// Runs at container startup before the gateway starts
//
// IMPORTANT: The gateway sets Content-Security-Policy: script-src 'self'
// which blocks inline scripts. So we must create an EXTERNAL .js file
// and reference it via <script src="./auto-token.js"> to satisfy CSP.
const fs = require('fs');
const htmlPath = '/app/dist/control-ui/index.html';
const jsPath = '/app/dist/control-ui/auto-token.js';
const token = process.env.OPENCLAW_GATEWAY_TOKEN;

if (token && fs.existsSync(htmlPath)) {
  // 1. Create external JS file with token-setting code
  const jsCode = [
    '(function() {',
    '  var k = "openclaw.control.settings.v1";',
    '  var s = {};',
    '  try { s = JSON.parse(localStorage.getItem(k) || "{}"); } catch(e) {}',
    '  s.token = "' + token + '";',
    '  s.gatewayUrl = (location.protocol === "https:" ? "wss://" : "ws://") + location.host;',
    '  localStorage.setItem(k, JSON.stringify(s));',
    '})();',
  ].join('\n');
  fs.writeFileSync(jsPath, jsCode);

  // 2. Inject <script src> tag as first element in <head> (satisfies CSP 'self')
  let html = fs.readFileSync(htmlPath, 'utf8');
  // Remove any previous injection (inline or external)
  html = html.replace(/<script[^>]*auto-token[^>]*>[^<]*<\/script>/g, '');
  html = html.replace(/<script[^>]*src="\.\/auto-token\.js"[^>]*><\/script>/g, '');
  // Add external script reference at start of <head>
  html = html.replace('<head>', '<head><script src="./auto-token.js"></script>');
  fs.writeFileSync(htmlPath, html);

  console.log('[inject-token] Created auto-token.js and injected <script src> into Control UI');
} else if (!token) {
  console.log('[inject-token] No OPENCLAW_GATEWAY_TOKEN set, skipping');
} else {
  console.log('[inject-token] Control UI HTML not found at', htmlPath);
}
