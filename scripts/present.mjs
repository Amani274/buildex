import {spawn} from 'node:child_process';
import {existsSync} from 'node:fs';

if (existsSync('.env')) process.loadEnvFile('.env');
if (!existsSync('dist/index.html')) {
  console.error('Build the presentation first: pnpm build');
  process.exit(1);
}
// Each fresh rehearsal uses a new database; earlier work is preserved.
const fresh = process.argv.includes('--fresh');
const database = fresh
  ? `data/presentations/demo-${new Date().toISOString().replace(/[:.]/g, '-')}.sqlite`
  : 'data/presentation.sqlite';
console.log(`Yebbo presentation: http://127.0.0.1:${process.env.PORT || 4000}`);
console.log(`Demo database: ${database}`);
const child = spawn(process.execPath, ['apps/server/src/index.ts'], {
  stdio: 'inherit',
  env: {...process.env, YEBBO_DB: database},
});
child.on('error', error => {console.error(error.message); process.exitCode = 1;});
child.on('exit', code => {process.exitCode = code || 0;});
process.on('SIGINT', () => child.kill());
process.on('SIGTERM', () => child.kill());
