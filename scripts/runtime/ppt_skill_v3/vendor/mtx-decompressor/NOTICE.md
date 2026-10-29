# Third-party dependency notice

- Component: mtx-decompressor 1.8.0 (ChristopherVR; TypeScript port of libeot by Brennan Vincent).
- License: MPL-2.0; see LICENSE alongside this file. Upstream module is distributed unchanged.
- Package: https://registry.npmjs.org/mtx-decompressor/-/mtx-decompressor-1.8.0.tgz
- Corresponding source: https://github.com/ChristopherVR/mtx-decompressor (version 1.8.0).
- Upstream metadata retained in package.json. The module includes source module annotations.
- index.mjs SHA-256: `cac9cfed06484c4bf77a97aed556c028a5df0d897e95d437db00daaf8aafe9cd`

The wrapper decode_eot.mjs is maintained separately by PPT Skill. No network or npm install occurs during font recovery. Requires Node.js 18+; Python dependencies remain in scripts/portable-requirements.txt. Missing runtime is recorded and only the source-content inspection route may use a substitute font copy.
