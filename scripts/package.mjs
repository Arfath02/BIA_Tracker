import fs from 'node:fs';
fs.mkdirSync('dist/server',{recursive:true});
fs.copyFileSync('dist/worker.js','dist/server/index.js');
const config=JSON.parse(fs.readFileSync('wrangler.json'));
config.main='index.js';config.assets.directory='../client';
config.d1_databases=config.d1_databases.map(b=>({...b,migrations_dir:'../../migrations'}));
fs.writeFileSync('dist/server/wrangler.json',JSON.stringify(config,null,2));
