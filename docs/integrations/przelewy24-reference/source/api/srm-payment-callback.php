<?php
/**
 * SRM Payment Callback — Przelewy24 urlStatus Handler
 * POST /api/srm-payment-callback.php
 *
 * Receives payment notification from P24,
 * verifies transaction, updates order status.
 */

header('Content-Type: application/json');
require_once __DIR__ . '/_security.php';

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    exit;
}

/* ═══ P24 CREDENTIALS ═══ */
define('P24_MERCHANT_ID', (int)be_required_secret('P24_MERCHANT_ID'));
define('P24_POS_ID',      (int)be_required_secret('P24_POS_ID'));
define('P24_API_KEY',     be_required_secret('P24_API_KEY'));
define('P24_CRC',         be_required_secret('P24_CRC'));
define('P24_BASE_URL',    rtrim(be_secret('P24_BASE_URL', 'https://secure.przelewy24.pl'), '/'));

/* ═══ READ NOTIFICATION ═══ */
$raw = file_get_contents('php://input');
$notification = json_decode($raw, true);

$logDir = '/home/u285877296/logs';
if (!is_dir($logDir)) @mkdir($logDir, 0755, true);

/* Log every callback */
file_put_contents($logDir . '/p24_callbacks.log',
    date('Y-m-d H:i:s') . " | RAW: {$raw}\n",
    FILE_APPEND
);

if (!$notification || !isset($notification['sessionId']) || !isset($notification['orderId'])) {
    http_response_code(400);
    echo json_encode(['error' => 'Invalid notification']);
    exit;
}

$sessionId  = $notification['sessionId'];
$orderId    = intval($notification['orderId']);
$amount     = intval($notification['amount']);
$currency   = $notification['currency'] ?? 'PLN';

/* ═══ VERIFY SIGN from P24 ═══ */
$receivedSign = $notification['sign'] ?? '';
$expectedSignData = json_encode([
    'sessionId'  => $sessionId,
    'orderId'    => $orderId,
    'amount'     => $amount,
    'currency'   => $currency,
    'crc'        => P24_CRC
], JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
$expectedSign = hash('sha384', $expectedSignData);

if ($receivedSign !== $expectedSign) {
    file_put_contents($logDir . '/p24_errors.log',
        date('Y-m-d H:i:s') . " | SIGN MISMATCH | session={$sessionId}\n",
        FILE_APPEND
    );
    http_response_code(400);
    echo json_encode(['error' => 'Invalid sign']);
    exit;
}

/* ═══ VERIFY TRANSACTION WITH P24 ═══ */
$verifySign = hash('sha384', json_encode([
    'sessionId'  => $sessionId,
    'orderId'    => $orderId,
    'amount'     => $amount,
    'currency'   => $currency,
    'crc'        => P24_CRC
], JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES));

$verifyPayload = [
    'merchantId' => P24_MERCHANT_ID,
    'posId'      => P24_POS_ID,
    'sessionId'  => $sessionId,
    'amount'     => $amount,
    'currency'   => $currency,
    'orderId'    => $orderId,
    'sign'       => $verifySign
];

$ch = curl_init(P24_BASE_URL . '/api/v1/transaction/verify');
curl_setopt_array($ch, [
    CURLOPT_POST           => true,
    CURLOPT_RETURNTRANSFER => true,
    CURLOPT_HTTPHEADER     => [
        'Content-Type: application/json',
        'Authorization: Basic ' . base64_encode(P24_POS_ID . ':' . P24_API_KEY),
    ],
    CURLOPT_POSTFIELDS     => json_encode($verifyPayload, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES),
    CURLOPT_TIMEOUT        => 15,
]);

$response = curl_exec($ch);
$httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
curl_close($ch);

$verifyData = json_decode($response, true);

file_put_contents($logDir . '/p24_callbacks.log',
    date('Y-m-d H:i:s') . " | VERIFY: {$httpCode} | {$response}\n",
    FILE_APPEND
);

/* ═══ UPDATE ORDER STATUS ═══ */
$orderDir  = '/home/u285877296/srm_orders';
$orderFile = $orderDir . '/' . $sessionId . '.json';

if (file_exists($orderFile)) {
    $order = json_decode(file_get_contents($orderFile), true);
    $wasAlreadyPaid = (($order['status'] ?? '') === 'paid');

    if ($httpCode === 200 && isset($verifyData['data']['status']) && $verifyData['data']['status'] === 'success') {
        $order['status']     = 'paid';
        $order['orderId']    = $orderId;
        $order['paidAt']     = $order['paidAt'] ?? date('c');
    } else {
        $order['status']     = 'verify_failed';
        $order['orderId']    = $orderId;
        $order['verifyCode'] = $httpCode;
        $order['verifyResp'] = $verifyData;
    }

    file_put_contents($orderFile, json_encode($order, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE));

    /* ═══ SEND NOTIFICATION EMAIL ═══ */
    if ($order['status'] === 'paid' && !$wasAlreadyPaid) {
        // Track Purchase in PostHog
        require_once __DIR__ . '/posthog.php';
        posthog_capture('Purchase Completed', $order['email'] ?? '', [
            'product' => $order['description'] ?? 'Unknown',
            'amount' => isset($order['brutto']) ? (float)$order['brutto'] : 0,
            'plan' => $order['plan'] ?? '',
            'orderId' => $orderId,
            'sessionId' => $sessionId
        ]);

        $company = $order['company'] ?? 'Brak';
        $plan    = $order['plan'] ?? '';
        $description = $order['description'] ?? '';
        $isSeoPogotowie = stripos($description, 'SEO Pogotowie') !== false;
        $productName = $isSeoPogotowie ? 'SEO Pogotowie' : 'SRM';
        $subject = $isSeoPogotowie
            ? "✅ Nowe zamówienie SEO Pogotowie — {$company}"
            : "✅ Nowe zamówienie SRM — {$company} ({$plan})";
        $body  = "Zamówienie opłacone!\n\n";
        $body .= "Produkt:  " . ($description ?: $productName) . "\n";
        $body .= "Firma:    " . ($order['company'] ?? '') . "\n";
        $body .= "NIP:      " . ($order['nip'] ?? '') . "\n";
        $body .= "Kontakt:  " . ($order['fullName'] ?? '') . "\n";
        $body .= "E-mail:   " . ($order['email'] ?? '') . "\n";
        $body .= "Telefon:  " . ($order['phone'] ?? '') . "\n";
        $body .= "Sklep:    " . ($order['storeUrl'] ?? '') . "\n";
        $body .= "Pakiet:   " . ($order['plan'] ?? '') . "\n";
        $body .= "Brutto:   " . ($order['brutto'] ?? '') . " PLN\n";
        if (!empty($order['referralSource']) || !empty($order['referralCampaign']) || !empty($order['referralEmail'])) {
            $body .= "\nŹródło kampanii:\n";
            $body .= "UTM source:   " . ($order['referralSource'] ?? '') . "\n";
            $body .= "UTM medium:   " . ($order['referralMedium'] ?? '') . "\n";
            $body .= "UTM campaign: " . ($order['referralCampaign'] ?? '') . "\n";
            $body .= "Email z kampanii: " . ($order['referralEmail'] ?? '') . "\n";
            $body .= "Domena email:     " . ($order['referralDomain'] ?? '') . "\n";
        }
        $body .= "Session:  {$sessionId}\n";
        $body .= "Order ID: {$orderId}\n";
        $body .= "Data:     " . date('Y-m-d H:i:s') . "\n";

        mail('kontakt@booster-engine.pl', $subject, $body,
            "From: noreply@booster-engine.pl\r\nReply-To: {$order['email']}");

        if ($isSeoPogotowie && !empty($order['email'])) {
            $buyerSubject = "Potwierdzenie płatności — SEO Pogotowie";
            $buyerBody  = "Dzień dobry,\n\n";
            $buyerBody .= "potwierdzamy przyjęcie płatności za SEO Pogotowie.\n\n";
            $buyerBody .= "Kwota: " . ($order['brutto'] ?? '') . " PLN\n";
            $buyerBody .= "Session: {$sessionId}\n\n";
            $buyerBody .= "Następny krok: uzupełnij formularz diagnostyczny, jeśli nie został jeszcze wysłany:\n";
            $buyerBody .= "https://booster-engine.pl/seo-pogotowie/dziekujemy?payment=success&session=" . rawurlencode($sessionId) . "\n\n";
            $buyerBody .= "Booster Engine\nkontakt@booster-engine.pl\n";
            mail($order['email'], $buyerSubject, $buyerBody,
                "From: Booster Engine <kontakt@booster-engine.pl>\r\nReply-To: kontakt@booster-engine.pl");
        }
    }
}

echo json_encode(['status' => 'ok']);
