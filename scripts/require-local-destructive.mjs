#!/usr/bin/env node

const variable = 'LOCAL_DESTRUCTIVE';
const description = 'destructive cleanup/reset operations';

if (process.env[variable] !== 'yes') {
  console.error('[guard] Refusing to run ' + description + '. Set ' + variable + '=yes only for an explicit local operation.');
  process.exit(1);
}
