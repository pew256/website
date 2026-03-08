const https = require('https');
const fs = require('fs');

const url = 'https://upload.wikimedia.org/wikipedia/commons/d/d4/Credit_Suisse_Logo_2022.svg';

https.get(url, (res) => {
  let data = '';
  res.on('data', (chunk) => data += chunk);
  res.on('end', () => fs.writeFileSync('cs.svg', data));
});
