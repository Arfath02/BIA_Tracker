// Explicit local/test schema setup. Hosted requests never perform DDL.
import fs from 'node:fs/promises';
export async function initializeLocalDatabase(mf){
 const db=await mf.getD1Database('DB');
 const sql=await fs.readFile(new URL('../migrations/0001.sql',import.meta.url),'utf8');
 await db.batch(sql.split(';').map(s=>s.trim()).filter(Boolean).map(s=>db.prepare(s)));
}
