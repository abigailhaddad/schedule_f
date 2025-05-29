"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.dbConfig = void 0;
// src/lib/db/config.ts
var dotenv_1 = require("dotenv");
var path_1 = require("path");
// Load environment variables
var envPath = process.env.ENV_PATH || path_1.default.resolve(process.cwd(), '.env');
(0, dotenv_1.config)({ path: envPath });
// Get the database environment
var getDbEnvironment = function () {
    var _a;
    var dbEnv = (_a = process.env.DB_ENV) === null || _a === void 0 ? void 0 : _a.toLowerCase();
    // Validate the environment
    if (dbEnv !== 'local' && dbEnv !== 'preprod' && dbEnv !== 'prod') {
        console.warn("Invalid DB_ENV: \"".concat(dbEnv, "\". Defaulting to \"local\"."));
        return 'local';
    }
    return dbEnv;
};
// Get the appropriate database URL
var getDatabaseUrl = function () {
    var dbEnv = getDbEnvironment();
    // Map environment to URL
    var urlMap = {
        local: process.env.DATABASE_URL_LOCAL,
        preprod: process.env.DATABASE_URL_PREPROD,
        prod: process.env.DATABASE_URL_PROD
    };
    var dbUrl = urlMap[dbEnv];
    if (!dbUrl) {
        throw new Error("DATABASE_URL_".concat(dbEnv.toUpperCase(), " is not defined in environment variables"));
    }
    // Log which database we're using (but not the URL for security)
    if (typeof window === 'undefined' && process.env.NODE_ENV === 'development') {
        console.log("\uD83D\uDDC4\uFE0F  Using ".concat(dbEnv.toUpperCase(), " database"));
    }
    return dbUrl;
};
// Export the configuration
var getDbConfig = function () {
    var dbUrl = getDatabaseUrl();
    var dbEnv = getDbEnvironment();
    return {
        url: dbUrl,
        isProd: dbEnv === 'prod',
        isPreprod: dbEnv === 'preprod',
        isLocal: dbEnv === 'local',
        isDev: dbEnv === 'local', // Backward compatibility
        env: dbEnv
    };
};
exports.dbConfig = getDbConfig();
