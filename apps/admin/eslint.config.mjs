import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const eslintConfig = defineConfig([
    ...nextVitals,
    ...nextTs,
    {
        rules: {
            // react-hooks v6 (floated in by the 2026-07 lockfile regen) promotes
            // this to error; the flagged sites are conventional fetch-in-effect
            // patterns. Keep as warn — matching apps/web — until the
            // react-compiler idiom migration is done as its own change.
            "react-hooks/set-state-in-effect": "warn",
        },
    },
    globalIgnores([
        ".next/**",
        "out/**",
        "build/**",
        "next-env.d.ts",
    ]),
]);

export default eslintConfig;
