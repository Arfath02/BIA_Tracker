import {initializeLocalDatabase} from './local-db.mjs';
import {Miniflare} from 'miniflare';
const mf=new Miniflare({scriptPath:'dist/worker.js',modules:true,compatibilityDate:'2026-05-22',d1Databases:['DB'],d1Persist:'.wrangler/miniflare-db',assets:{directory:'dist/client',binding:'ASSETS',routerConfig:{invoke_user_worker_ahead_of_assets:true},assetConfig:{not_found_handling:'single-page-application'}},host:'127.0.0.1',port:8787,cf:false});
await initializeLocalDatabase(mf);
console.log('Review server:',(await mf.ready).href);
