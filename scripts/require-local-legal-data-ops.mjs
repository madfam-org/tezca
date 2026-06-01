#!/usr/bin/env node

const variable = 'LOCAL_LEGAL_DATA_OPS';
const description = 'legal ingestion/indexing/export/webhook/chat/package-publish operations';

if (process.env[variable] !== 'yes') {
  console.error('[guard] Refusing to run ' + description + '. Set ' + variable + '=yes only for an explicit local operation.');
  process.exit(1);
}
