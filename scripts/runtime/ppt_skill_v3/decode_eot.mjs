import fs from 'node:fs';
import { eotToTtf, parseEotMetadata } from './vendor/mtx-decompressor/index.mjs';

try {
  const bytes = new Uint8Array(fs.readFileSync(process.argv[2]));
  const meta = parseEotMetadata(bytes);
  if (meta.permissions & (2 | 256 | 512)) throw new Error('embedding_permission_restricted');
  if (meta.encrypted) throw new Error('xor_obfuscated_eot_requires_separate_support');
  const warnings = [];
  const font = eotToTtf(bytes, { onWarn: warning => warnings.push(warning) });
  fs.writeFileSync(process.argv[3], font);
  process.stdout.write(JSON.stringify({tool: 'mtx-decompressor', version: '1.8.0',
    compressed: meta.compressed, fsType: meta.permissions, warnings}));
} catch (error) {
  process.stderr.write(JSON.stringify({code: error.code || 'EOT_DECODE_ERROR', message: error.message}));
  process.exitCode = 1;
}
