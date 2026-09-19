<?php
declare(strict_types=1);

function be_load_secrets(): array {
    static $secrets = null;
    if ($secrets !== null) {
        return $secrets;
    }

    $secrets = [];
    $paths = [
        dirname(__DIR__, 2) . '/booster-engine-secrets.php',
        dirname(__DIR__) . '/../booster-engine-secrets.php',
    ];

    foreach ($paths as $path) {
        if (is_file($path)) {
            $loaded = require $path;
            if (is_array($loaded)) {
                $secrets = array_merge($secrets, $loaded);
            }
        }
    }

    return $secrets;
}

function be_secret(string $key, ?string $default = null): ?string {
    $env = getenv($key);
    if ($env !== false && $env !== '') {
        return $env;
    }
    if (isset($_ENV[$key]) && $_ENV[$key] !== '') {
        return (string)$_ENV[$key];
    }
    if (isset($_SERVER[$key]) && $_SERVER[$key] !== '') {
        return (string)$_SERVER[$key];
    }

    $secrets = be_load_secrets();
    return isset($secrets[$key]) && $secrets[$key] !== '' ? (string)$secrets[$key] : $default;
}

function be_required_secret(string $key): string {
    $value = be_secret($key);
    if ($value === null || $value === '') {
        http_response_code(500);
        echo json_encode(['error' => 'Server configuration missing.']);
        exit;
    }
    return $value;
}

function be_apply_cors(array $methods = ['POST', 'OPTIONS'], array $allowedOrigins = ['https://booster-engine.pl', 'https://www.booster-engine.pl']): void {
    $origin = $_SERVER['HTTP_ORIGIN'] ?? '';
    if ($origin && in_array($origin, $allowedOrigins, true)) {
        header('Access-Control-Allow-Origin: ' . $origin);
        header('Vary: Origin');
    }
    header('Access-Control-Allow-Methods: ' . implode(', ', $methods));
    header('Access-Control-Allow-Headers: Content-Type, Authorization');
}

function be_client_ip(): string {
    $ip = $_SERVER['HTTP_CF_CONNECTING_IP'] ?? $_SERVER['HTTP_X_REAL_IP'] ?? $_SERVER['REMOTE_ADDR'] ?? 'unknown';
    if (strpos($ip, ',') !== false) {
        $ip = trim(explode(',', $ip)[0]);
    }
    return preg_replace('/[^a-fA-F0-9:.,_-]/', '', $ip) ?: 'unknown';
}

function be_rate_limit(string $scope, string $identity, int $limit, int $windowSeconds, string $message = 'Too many requests.'): void {
    $dir = sys_get_temp_dir() . '/booster-engine-rate';
    if (!is_dir($dir)) {
        @mkdir($dir, 0755, true);
    }

    $file = $dir . '/' . preg_replace('/[^a-zA-Z0-9_-]/', '_', $scope) . '_' . hash('sha256', $identity) . '.json';
    $now = time();
    $hits = [];

    if (is_file($file)) {
        $decoded = json_decode((string)file_get_contents($file), true);
        if (is_array($decoded)) {
            $hits = array_values(array_filter($decoded, fn($ts) => is_int($ts) && $ts > $now - $windowSeconds));
        }
    }

    if (count($hits) >= $limit) {
        http_response_code(429);
        echo json_encode(['error' => $message]);
        exit;
    }

    $hits[] = $now;
    file_put_contents($file, json_encode($hits), LOCK_EX);
}

function be_min_interval(string $scope, string $identity, int $seconds, string $message = 'Please wait before retrying.'): void {
    be_rate_limit($scope, $identity, 1, $seconds, $message);
}

function be_honeypot(array $data, array $fields = ['website', 'url2', 'company_website', 'homepage']): void {
    foreach ($fields as $field) {
        if (!empty($data[$field])) {
            usleep(350000);
            http_response_code(400);
            echo json_encode(['error' => 'Request rejected.']);
            exit;
        }
    }
}

function be_delay_ms(int $milliseconds): void {
    if ($milliseconds > 0) {
        usleep(min($milliseconds, 2000) * 1000);
    }
}
