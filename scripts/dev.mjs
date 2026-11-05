import {spawn} from 'node:child_process';
const processes = [spawn(process.execPath,['--watch','apps/server/src/index.ts'],{stdio:'inherit'}),spawn(process.execPath,['node_modules/vite/bin/vite.js','--config','apps/dashboard/vite.config.ts','--host','127.0.0.1'],{stdio:'inherit'})];
for(const p of processes) p.on('exit',code=>{if(code) {processes.forEach(x=>x.kill());process.exit(code);}});
process.on('SIGINT',()=>{processes.forEach(p=>p.kill());process.exit();});
