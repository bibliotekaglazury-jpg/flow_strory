<?php
/**
 * Przelewy24 Sandbox — Transaction Register
 * Registers a transaction and returns the redirect URL
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

// ═══ P24 Production Config ═══
$P24_MERCHANT_ID = (int)be_required_secret('P24_MERCHANT_ID');
$P24_POS_ID      = (int)be_required_secret('P24_POS_ID');
$P24_CRC         = be_required_secret('P24_CRC');
$P24_API_KEY     = be_required_secret('P24_API_KEY');
$P24_BASE_URL    = rtrim(be_secret('P24_BASE_URL', 'https://secure.przelewy24.pl'), '/');
$P24_API_URL     = $P24_BASE_URL . '/api/v1';
$P24_REDIRECT    = $P24_BASE_URL . '/trnRequest/';

// ═══ Get input ═══
$input = json_decode(file_get_contents('php://input'), true);
if (!$input) {
    http_response_code(400);
    echo json_encode(['error' => 'Invalid JSON input']);
    exit;
}
be_honeypot($input, ['website', 'url2', 'company_website', 'homepage']);
be_delay_ms(150);
be_rate_limit('p24_register_ip_hour', be_client_ip(), 12, 3600, 'Too many payment attempts.');
be_min_interval('p24_register_ip_interval', be_client_ip(), 5, 'Please wait before retrying.');

$sessionId  = 'SRM-' . time() . '-' . mt_rand(1000, 9999);
$amountPLN  = floatval($input['amount'] ?? 0);     // brutto in PLN
$amountGr   = (int)round($amountPLN * 100);         // grosze (cents)
$email      = $input['email'] ?? '';
$client     = $input['client'] ?? $input['full_name'] ?? '';
$company    = $input['company_name'] ?? $input['company'] ?? '';
$nip        = $input['nip'] ?? '';
$phone      = $input['phone'] ?? '';
$storeUrl   = $input['store_url'] ?? '';
$description = $input['description'] ?? 'SEO Redirect Manager';
$payMethod  = $input['payment_method'] ?? 'blik';
$referralSource = $input['referral_source'] ?? '';
$referralCampaign = $input['referral_campaign'] ?? '';
$referralMedium = $input['referral_medium'] ?? '';
$referralEmail = $input['referral_email'] ?? '';
$referralDomain = $input['referral_domain'] ?? '';
if ($email) {
    be_rate_limit('p24_register_email_hour', strtolower((string)$email), 6, 3600, 'Too many payment attempts for this email.');
}

// Channel removed — P24 shows all available payment methods

// Return URL — dynamic based on product
$isSrm = (stripos($description, 'Redirect') !== false || stripos($description, 'SRM') !== false);
$isIG  = (stripos($description, 'Index Guard') !== false);
$isLLM = (stripos($description, 'LLM.txt') !== false || stripos($description, 'LLM') !== false);
$isSeoPogotowie = (stripos($description, 'SEO Pogotowie') !== false);
if ($isSrm) {
    $returnPage = '/seo-redirect-manager';
} elseif ($isIG) {
    $returnPage = '/apps/index-guard/landing/';
} elseif ($isLLM) {
    $returnPage = '/apps/llm.txt/landing/';
} elseif ($isSeoPogotowie) {
    $returnPage = '/seo-pogotowie/dziekujemy';
} else {
    $returnPage = '/ai-visibility-booster';
}
$urlReturn = 'https://booster-engine.pl' . $returnPage . '?payment=success&session=' . urlencode($sessionId);
$urlStatus = 'https://booster-engine.pl/api/srm-payment-callback.php';

// ═══ Calculate sign ═══
$signData = json_encode([
    'sessionId'  => $sessionId,
    'merchantId' => $P24_MERCHANT_ID,
    'amount'     => $amountGr,
    'currency'   => 'PLN',
    'crc'        => $P24_CRC
], JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);

$sign = hash('sha384', $signData);

// ═══ Register transaction ═══
$payload = [
    'merchantId'       => $P24_MERCHANT_ID,
    'posId'            => $P24_POS_ID,
    'sessionId'        => $sessionId,
    'amount'           => $amountGr,
    'currency'         => 'PLN',
    'description'      => $description,
    'email'            => $email,
    'client'           => $client,
    'country'          => 'PL',
    'language'         => 'pl',
    'urlReturn'        => $urlReturn,
    'urlStatus'        => $urlStatus,

    'sign'             => $sign,
    'encoding'         => 'UTF-8',
    'regulationAccept' => true
];

$ch = curl_init($P24_API_URL . '/transaction/register');
curl_setopt_array($ch, [
    CURLOPT_POST           => true,
    CURLOPT_POSTFIELDS     => json_encode($payload),
    CURLOPT_RETURNTRANSFER => true,
    CURLOPT_HTTPHEADER     => ['Content-Type: application/json'],
    CURLOPT_USERPWD        => $P24_POS_ID . ':' . $P24_API_KEY,
    CURLOPT_TIMEOUT        => 15
]);

$response = curl_exec($ch);
$httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
$curlError = curl_error($ch);
curl_close($ch);

if ($curlError) {
    http_response_code(500);
    echo json_encode(['error' => 'cURL error: ' . $curlError]);
    exit;
}

$result = json_decode($response, true);

if (($httpCode === 200 || $httpCode === 201) && isset($result['data']['token'])) {
    $token = $result['data']['token'];
    // Log order
    $logEntry = date('Y-m-d H:i:s') . " | $sessionId | $email | $amountPLN PLN | $payMethod | token=$token\n";
    file_put_contents(__DIR__ . '/orders.log', $logEntry, FILE_APPEND | LOCK_EX);

    // Save order to JSON so srm-payment-callback.php can process it
    $orderDir = '/home/u285877296/srm_orders';
    if (!is_dir($orderDir)) @mkdir($orderDir, 0755, true);

    $orderData = [
        'sessionId'   => $sessionId,
        'token'       => $token,
        'plan'        => 'jednorazowa licencja',
        'netto'       => round($amountPLN / 1.23, 2),
        'brutto'      => $amountPLN,
        'company'     => $company,
        'nip'         => $nip,
        'fullName'    => $client,
        'email'       => $email,
        'phone'       => $phone,
        'storeUrl'    => $storeUrl,
        'payMethod'   => $payMethod,
        'description' => $description,
        'referralSource' => $referralSource,
        'referralCampaign' => $referralCampaign,
        'referralMedium' => $referralMedium,
        'referralEmail' => $referralEmail,
        'referralDomain' => $referralDomain,
        'status'      => 'pending',
        'createdAt'   => date('c')
    ];
    file_put_contents($orderDir . '/' . $sessionId . '.json', json_encode($orderData, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE));

    echo json_encode([
        'success'     => true,
        'token'       => $token,
        'redirectUrl' => $P24_REDIRECT . $token,
        'sessionId'   => $sessionId
    ]);
} else {
    http_response_code($httpCode ?: 500);
    echo json_encode([
        'error'    => 'P24 registration failed',
        'httpCode' => $httpCode,
        'response' => $result
    ]);
}
