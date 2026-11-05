import {existsSync} from 'node:fs';
import {Store} from './db.ts';
import {createApp} from './app.ts';
if(existsSync('.env'))process.loadEnvFile('.env');
if(process.env.NODE_ENV==='production')throw Error('This local development backend is not configured for public production hosting. See docs/DEPLOYMENT.md.');
const store=new Store(process.env.YEBBO_DB||'data/yebbo.sqlite');
const server=createApp(store).listen(Number(process.env.PORT||4000),process.env.HOST||'127.0.0.1',()=>console.log('Yebbo API ready at http://'+(process.env.HOST||'127.0.0.1')+':'+(process.env.PORT||4000)));
function shutdown(){server.close(()=>{store.close();process.exit();});}process.on('SIGINT',shutdown);process.on('SIGTERM',shutdown);
