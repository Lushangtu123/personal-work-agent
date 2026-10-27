import { strict as assert } from 'node:assert';
import { complete } from './support/finalize.mjs';

assert.equal(2 + 2, 4);
await complete();
