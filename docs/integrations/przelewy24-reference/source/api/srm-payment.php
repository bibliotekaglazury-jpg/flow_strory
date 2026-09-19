<?php
/**
 * SRM Payment — Przelewy24 REST API Integration
 * POST /api/srm-payment.php
 *
 * Receives checkout data from frontend, registers transaction
 * at Przelewy24, returns payment redirect URL.
 */

header('Content-Type: application/json');
require_once __DIR__ . '/_security.php';
be_apply_cors(['POST', 'OPTIONS']);

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') { exit(0); }
if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo json_encode(['error' => 'Method not allowed']);
    exit;
}

/* ═══ P24 CREDENTIALS ═══ */
define('P24_MERCHANT_ID', (int)be_required_secret('P24_MERCHANT_ID'));
define('P24_POS_ID',      (int)be_required_secret('P24_POS_ID'));
define('P24_API_KEY',     be_required_secret('P24_API_KEY'));
define('P24_CRC',         be_required_secret('P24_CRC'));
define('P24_BASE_URL',    rtrim(be_secret('P24_BASE_URL', 'https://secure.przelewy24.pl'), '/'));

/* ═══ READ INPUT ═══ */
$input = json_decode(file_get_contents('php://input'), true);
if (!$input) {
    http_response_code(400);
    echo json_encode(['error' => 'Invalid JSON']);
    exit;
}
be_honeypot($input, ['website', 'url2', 'company_website', 'homepage']);
be_delay_ms(150);
be_rate_limit('srm_payment_ip_hour', be_client_ip(), 12, 3600, 'Too many payment attempts.');
be_min_interval('srm_payment_ip_interval', be_client_ip(), 5, 'Please wait before retrying.');

$fullName    = trim($input['full_name'] ?? '');
$company     = trim($input['company_name'] ?? '');
$nip         = preg_replace('/\D/', '', $input['nip'] ?? '');
$phone       = '+48' . preg_replace('/\D/', '', $input['phone'] ?? '');
$email       = trim($input['email'] ?? '');
$storeUrl    = trim($input['store_url'] ?? '');
$street      = trim($input['street'] ?? '');
$postalCode  = trim($input['postal_code'] ?? '');
$city        = trim($input['city'] ?? '');
$plan        = trim($input['plan'] ?? 'miesięczny');
$nettoAmount = intval($input['netto'] ?? 100);
$payMethod   = trim($input['payment_method'] ?? 'blik');
if ($email) {
    be_rate_limit('srm_payment_email_hour', strtolower($email), 6, 3600, 'Too many payment attempts for this email.');
}

/* Validate required fields */
if (!$fullName || !$company || !$email || !$storeUrl || strlen($nip) !== 10) {
    http_response_code(400);
    echo json_encode(['error' => 'Missing required fields']);
    exit;
}

/* Calculate amounts in grosz */
$vatAmount   = round($nettoAmount * 0.23);
$bruttoGrosze = ($nettoAmount + $vatAmount) * 100;

/* Session ID — unique per transaction */
$sessionId = 'SRM_' . time() . '_' . bin2hex(random_bytes(4));

/* Description */
$planLabel = $plan === 'roczny' ? 'Roczny (12 mies.)' : 'Miesięczny';
$description = "SEO Redirect Manager — Pakiet {$planLabel} — {$company}";

/* ═══ SIGN: SHA384 of JSON ═══ */
$signData = json_encode([
    'sessionId'  => $sessionId,
    'merchantId' => P24_MERCHANT_ID,
    'amount'     => $bruttoGrosze,
    'currency'   => 'PLN',
    'crc'        => P24_CRC
], JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);

$sign = hash('sha384', $signData);

/* ═══ REGISTER TRANSACTION ═══ */
$payload = [
    'merchantId'  => P24_MERCHANT_ID,
    'posId'       => P24_POS_ID,
    'sessionId'   => $sessionId,
    'amount'      => $bruttoGrosze,
    'currency'    => 'PLN',
    'description' => $description,
    'email'       => $email,
    'client'      => $fullName,
    'phone'       => $phone,
    'country'     => 'PL',
    'language'    => 'pl',
    'urlReturn'   => 'https://booster-engine.pl/seo-redirect-manager?payment=success&session=' . urlencode($sessionId),
    'urlStatus'   => 'https://booster-engine.pl/api/srm-payment-callback.php',
    'sign'        => $sign,
];

/* Map payment method to P24 method ID */
$methodMap = [
    'blik'               => 150,
    'karta'              => 218,
    'przelew_online'     => null,  // all methods
    'przelew_tradycyjny' => 136,
];
if (isset($methodMap[$payMethod]) && $methodMap[$payMethod] !== null) {
    $payload['method'] = $methodMap[$payMethod];
}

$ch = curl_init(P24_BASE_URL . '/api/v1/transaction/register');
curl_setopt_array($ch, [
    CURLOPT_POST           => true,
    CURLOPT_RETURNTRANSFER => true,
    CURLOPT_HTTPHEADER     => [
        'Content-Type: application/json',
        'Authorization: Basic ' . base64_encode(P24_POS_ID . ':' . P24_API_KEY),
    ],
    CURLOPT_POSTFIELDS     => json_encode($payload, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES),
    CURLOPT_TIMEOUT        => 15,
]);

$response = curl_exec($ch);
$httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
$curlErr  = curl_error($ch);
curl_close($ch);

if ($curlErr) {
    http_response_code(500);
    echo json_encode(['error' => 'P24 connection error', 'detail' => $curlErr]);
    exit;
}

$data = json_decode($response, true);

if ($httpCode >= 400 || !isset($data['data']['token'])) {
    http_response_code(502);
    echo json_encode([
        'error'    => 'P24 registration failed',
        'httpCode' => $httpCode,
        'response' => $data
    ]);

    /* Log the error */
    $logDir = dirname(__DIR__) . '/logs';
    if (!is_dir($logDir)) @mkdir($logDir, 0755, true);
    file_put_contents($logDir . '/p24_errors.log',
        date('Y-m-d H:i:s') . " | {$httpCode} | {$response}\n",
        FILE_APPEND
    );
    exit;
}

$token = $data['data']['token'];

/* ═══ SAVE ORDER TO FILE ═══ */
$orderDir = '/home/u285877296/srm_orders';
if (!is_dir($orderDir)) @mkdir($orderDir, 0755, true);

$order = [
    'sessionId'   => $sessionId,
    'token'       => $token,
    'plan'        => $plan,
    'netto'       => $nettoAmount,
    'brutto'      => $bruttoGrosze / 100,
    'company'     => $company,
    'nip'         => $nip,
    'fullName'    => $fullName,
    'email'       => $email,
    'phone'       => $phone,
    'storeUrl'    => $storeUrl,
    'address'     => "{$street}, {$postalCode} {$city}",
    'payMethod'   => $payMethod,
    'status'      => 'pending',
    'createdAt'   => date('c'),
];

file_put_contents(
    $orderDir . '/' . $sessionId . '.json',
    json_encode($order, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE)
);

/* ═══ RETURN REDIRECT URL ═══ */
echo json_encode([
    'success'     => true,
    'redirectUrl' => P24_BASE_URL . '/trnRequest/' . $token,
    'sessionId'   => $sessionId
]);
