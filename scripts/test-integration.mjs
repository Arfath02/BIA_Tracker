import {spawnSync} from 'node:child_process';
for (const name of ['api','admin-api','masters-api','access-api','management-api','auth-ui','baseline-ui','scheduling-ui','commercial-ui','budget-gantt-ui','approval-inbox-ui']) {
 const result=spawnSync(process.execPath,[`tests/${name}.mjs`],{stdio:'inherit'});
 if(result.status!==0) process.exit(result.status||1);
}
