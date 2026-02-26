// k6 load test: Browse endpoints (law list, detail, articles)
//
// Usage:
//   k6 run tests/load/browse.js
//   k6 run tests/load/browse.js --env BASE_URL=https://api.tezca.mx/api/v1
//
// Default thresholds: p95 < 200ms for detail, error rate < 1%

import http from 'k6/http';
import { check, group, sleep } from 'k6';

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000/api/v1';

// Sample law IDs — replace with real IDs from your deployment
const SAMPLE_LAW_IDS = [
    'cpeum',
    'ley_federal_del_trabajo',
    'codigo_civil_federal',
    'ley_general_de_salud',
    'ley_de_amparo',
];

export const options = {
    stages: [
        { duration: '30s', target: 10 },
        { duration: '1m', target: 30 },
        { duration: '1m', target: 50 },
        { duration: '30s', target: 0 },
    ],
    thresholds: {
        'http_req_duration{name:law_list}': ['p(95)<300'],
        'http_req_duration{name:law_detail}': ['p(95)<200'],
        'http_req_duration{name:law_articles}': ['p(95)<500'],
        http_req_failed: ['rate<0.01'],
    },
};

export default function () {
    group('Law List', () => {
        const page = Math.floor(Math.random() * 5) + 1;
        const res = http.get(`${BASE_URL}/laws/?page=${page}`, {
            tags: { name: 'law_list' },
        });
        check(res, {
            'list: status 200': (r) => r.status === 200,
        });
    });

    sleep(0.5);

    group('Law Detail', () => {
        const lawId = SAMPLE_LAW_IDS[Math.floor(Math.random() * SAMPLE_LAW_IDS.length)];
        const res = http.get(`${BASE_URL}/laws/${lawId}/`, {
            tags: { name: 'law_detail' },
        });
        check(res, {
            'detail: status 200 or 404': (r) => r.status === 200 || r.status === 404,
        });
    });

    sleep(0.5);

    group('Law Articles', () => {
        const lawId = SAMPLE_LAW_IDS[Math.floor(Math.random() * SAMPLE_LAW_IDS.length)];
        const res = http.get(`${BASE_URL}/laws/${lawId}/articles/`, {
            tags: { name: 'law_articles' },
        });
        check(res, {
            'articles: status 200 or 404': (r) => r.status === 200 || r.status === 404,
        });
    });

    sleep(0.5 + Math.random());
}
