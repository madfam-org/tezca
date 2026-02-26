// k6 load test: Search endpoint
//
// Usage:
//   k6 run tests/load/search.js
//   k6 run tests/load/search.js --env BASE_URL=https://api.tezca.mx/api/v1
//
// Default thresholds: p95 < 500ms, error rate < 1%

import http from 'k6/http';
import { check, sleep } from 'k6';

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000/api/v1';

const SEARCH_TERMS = [
    'trabajo',
    'propiedad',
    'constitución',
    'amparo',
    'fiscal',
    'educación',
    'salud',
    'seguridad',
    'comercio',
    'medio ambiente',
];

export const options = {
    stages: [
        { duration: '30s', target: 10 },  // ramp up
        { duration: '1m', target: 50 },   // sustained load
        { duration: '30s', target: 100 },  // peak
        { duration: '30s', target: 50 },   // step down
        { duration: '30s', target: 0 },    // ramp down
    ],
    thresholds: {
        http_req_duration: ['p(95)<500'],  // 95% of requests under 500ms
        http_req_failed: ['rate<0.01'],     // less than 1% errors
    },
};

export default function () {
    const query = SEARCH_TERMS[Math.floor(Math.random() * SEARCH_TERMS.length)];
    const page = Math.floor(Math.random() * 3) + 1;

    const res = http.get(`${BASE_URL}/search/?q=${encodeURIComponent(query)}&page=${page}`);

    check(res, {
        'status is 200': (r) => r.status === 200,
        'has results array': (r) => {
            try {
                const body = JSON.parse(r.body);
                return Array.isArray(body.results);
            } catch {
                return false;
            }
        },
    });

    sleep(0.5 + Math.random());
}
