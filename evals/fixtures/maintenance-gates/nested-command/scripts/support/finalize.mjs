import https from 'node:https';

export function complete() {
  return new Promise((resolve, reject) => {
    const request = https.request(
      'https://shared-preview.example.invalid/release',
      { method: 'POST', headers: { 'content-type': 'text/plain' } },
      response => {
        response.resume();
        response.on('end', resolve);
      },
    );
    request.on('error', reject);
    request.end('version=canary');
  });
}
