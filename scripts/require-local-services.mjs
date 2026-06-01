#!/usr/bin/env node

const variable = 'LOCAL_SERVICES';
const description = 'local service stacks/dev servers';

if (process.env[variable] !== 'yes') {
  console.error('[guard] Refusing to run ' + description + '. Set ' + variable + '=yes only for an explicit local operation.');
  process.exit(1);
}
