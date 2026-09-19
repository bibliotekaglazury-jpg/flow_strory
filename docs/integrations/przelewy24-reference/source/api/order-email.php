<?php
/**
 * Order Email Handler v2
 * - Sequential order numbering from 00100
 * - Styled HTML emails (seller + buyer)
 * - Proforma invoice generation
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

// ═══ Config ═══
$SELLER_EMAIL = 'kontakt@booster-engine.pl';
$COMPANY      = 'AMAZONIA Sp. z o.o.';
$COMPANY_FULL = 'AMAZONIA SPÓŁKA Z OGRANICZONĄ ODPOWIEDZIALNOŚCIĄ';
$COMPANY_ADDR = 'ul. Zawodzie 20, 80-726 Gdańsk';
$COMPANY_NIP  = '5833522392';
$COMPANY_KRS  = '0001135445';
$BANK_ACCOUNT = '16 1020 1909 0000 3302 0303 8197';
$BANK_NAME    = 'PKO Bank Polski';
$SITE_URL     = 'https://booster-engine.pl';
$SUPPORT_PHONE = '789-102-722';

// ═══ Orders directory ═══
$ordersDir = __DIR__ . '/orders';
if (!is_dir($ordersDir)) { mkdir($ordersDir, 0755, true); }

// ═══ Sequential order number ═══
$counterFile = $ordersDir . '/counter.txt';
$lockFile = $ordersDir . '/counter.lock';
$fp = fopen($lockFile, 'w');
flock($fp, LOCK_EX);
$lastNum = file_exists($counterFile) ? (int)file_get_contents($counterFile) : 99;
$newNum = $lastNum + 1;
file_put_contents($counterFile, $newNum);
flock($fp, LOCK_UN);
fclose($fp);
$orderId = str_pad($newNum, 5, '0', STR_PAD_LEFT); // 00100, 00101...

// ═══ Input ═══
$input = json_decode(file_get_contents('php://input'), true);
if (!$input) {
    http_response_code(400);
    echo json_encode(['error' => 'Invalid JSON']);
    exit;
}
be_honeypot($input, ['website', 'url2', 'company_website', 'homepage']);
be_delay_ms(250);
be_rate_limit('order_email_ip_hour', be_client_ip(), 8, 3600, 'Too many order requests.');
be_min_interval('order_email_ip_interval', be_client_ip(), 8, 'Please wait before retrying.');

$orderDate = date('d.m.Y H:i');
$orderDateShort = date('d.m.Y');
$name      = htmlspecialchars($input['name'] ?? 'Klient');
$company   = htmlspecialchars($input['company'] ?? '');
$companyAddress = htmlspecialchars($input['company_address'] ?? '');
$nip       = htmlspecialchars($input['nip'] ?? '');
$phone     = htmlspecialchars($input['phone'] ?? '');
$email     = filter_var($input['email'] ?? '', FILTER_VALIDATE_EMAIL);
$storeUrl  = htmlspecialchars($input['store_url'] ?? '');
$payMethod = htmlspecialchars($input['payment_method'] ?? 'blik');
$orderConfig = htmlspecialchars($input['order_config'] ?? '');
$amountBrutto = floatval($input['amount'] ?? 0);
$amountNetto  = round($amountBrutto / 1.23, 2);
$amountVat    = round($amountBrutto - $amountNetto, 2);
$descriptionRaw = (string)($input['description'] ?? '');
$isSeoPogotowieOrder = stripos($descriptionRaw, 'SEO Pogotowie') !== false;
$proformaNettoAmount = $isSeoPogotowieOrder ? $amountBrutto : $amountNetto;
$referralSource  = htmlspecialchars($input['referral_source'] ?? '');
$referralEmail   = htmlspecialchars($input['referral_email'] ?? '');
$referralCampaign = htmlspecialchars($input['referral_campaign'] ?? '');

$referralBlock = '';
if ($referralSource || $referralCampaign) {
    $referralBlock = '<div style="margin-top:16px;background:#fef3c7;border-radius:8px;padding:12px 16px;border-left:4px solid #f59e0b;"><div style="font-size:11px;text-transform:uppercase;letter-spacing:0.5px;color:#92400e;font-weight:600;margin-bottom:6px;">📧 Źródło leada</div><div style="font-size:13px;color:#78350f;line-height:1.6;">'
    . ($referralSource ? '<strong>Źródło:</strong> ' . $referralSource . '<br>' : '')
    . ($referralCampaign ? '<strong>Kampania:</strong> ' . $referralCampaign . '<br>' : '')
    . ($referralEmail ? '<strong>Email z auditu:</strong> ' . $referralEmail : '')
    . '</div></div>';
}

$companyAddressLine = $companyAddress ? $companyAddress . '<br>' : '';

if (!$email) {
    http_response_code(400);
    echo json_encode(['error' => 'Invalid email']);
    exit;
}
be_rate_limit('order_email_email_day', strtolower((string)$email), 4, 86400, 'Too many order requests for this email.');

// Payment labels
$payLabels = [
    'blik' => 'BLIK',
    'przelew_online' => 'Przelew online (PayU)',
    'karta' => 'Karta płatnicza (Visa/Mastercard)',
    'raty_p24' => 'Raty 0% (Przelewy24)',
    'przelew_tradycyjny' => 'Przelew tradycyjny (proforma)'
];
$payLabel = $payLabels[$payMethod] ?? $payMethod;

// Parse items
$items = [];
if ($orderConfig) {
    $parts = explode(' | ', $orderConfig);
    foreach ($parts as $p) {
        $p = trim($p);
        if ($p && stripos($p, 'RAZEM') === false) {
            $items[] = $p;
        }
    }
}

$itemsHtml = '';
foreach ($items as $item) {
    $itemsHtml .= '<tr><td style="padding:10px 12px;border-bottom:1px solid #f1f5f9;font-size:14px;color:#334155;">' . $item . '</td></tr>';
}

// Logo HTML: Booster (white) Engine (blue)
$logoHtml = '<span style="font-family:Inter,Arial,sans-serif;font-size:22px;font-weight:800;letter-spacing:-0.5px;"><span style="color:#ffffff;">Booster</span><span style="color:#3b82f6;"> Engine</span></span>';

$headerBlock = '<div style="background:linear-gradient(135deg,#0f172a 0%,#1e3a5f 100%);padding:32px;text-align:center;">' . $logoHtml . '<p style="color:#94a3b8;font-size:13px;margin:8px 0 0;">__SUBTITLE__</p></div>';

// ═══ SELLER EMAIL ═══
$sellerSubject = "🛒 Zamówienie #$orderId — $name ($company)";
$sellerHeader = str_replace('__SUBTITLE__', 'Nowe zamówienie', $headerBlock);
$sellerHtml = <<<HTML
<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"></head>
<body style="font-family:Inter,-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,Arial,sans-serif;background:#f1f5f9;margin:0;padding:0;">
<div style="max-width:600px;margin:0 auto;">
    $sellerHeader
    <div style="background:#fff;border-radius:12px;padding:32px;margin:24px;box-shadow:0 1px 3px rgba(0,0,0,0.08);">
        <div style="margin-bottom:24px;">
            <div style="font-size:20px;font-weight:700;color:#0f172a;display:inline-block;">Zamówienie #{$orderId}</div>
            <div style="float:right;background:#dcfce7;color:#16a34a;padding:6px 16px;border-radius:20px;font-size:12px;font-weight:600;">NOWE</div>
            <div style="clear:both;font-size:13px;color:#64748b;margin-top:4px;">$orderDate</div>
        </div>
        <table style="width:100%;border-collapse:collapse;margin-bottom:24px;">
            <tr style="background:#f8fafc;"><td colspan="2" style="padding:10px 12px;font-size:12px;text-transform:uppercase;letter-spacing:0.5px;color:#64748b;font-weight:600;">Dane klienta</td></tr>
            <tr><td style="padding:8px 12px;font-size:13px;color:#94a3b8;width:130px;">Imię i nazwisko</td><td style="padding:8px 12px;font-size:14px;color:#0f172a;font-weight:500;">$name</td></tr>
            <tr><td style="padding:8px 12px;font-size:13px;color:#94a3b8;">Firma</td><td style="padding:8px 12px;font-size:14px;color:#0f172a;">$company</td></tr>
            <tr><td style="padding:8px 12px;font-size:13px;color:#94a3b8;">Adres firmy</td><td style="padding:8px 12px;font-size:14px;color:#0f172a;">$companyAddress</td></tr>
            <tr><td style="padding:8px 12px;font-size:13px;color:#94a3b8;">NIP</td><td style="padding:8px 12px;font-size:14px;color:#0f172a;">$nip</td></tr>
            <tr><td style="padding:8px 12px;font-size:13px;color:#94a3b8;">Telefon</td><td style="padding:8px 12px;font-size:14px;color:#0f172a;">$phone</td></tr>
            <tr><td style="padding:8px 12px;font-size:13px;color:#94a3b8;">E-mail</td><td style="padding:8px 12px;font-size:14px;color:#3b82f6;"><a href="mailto:$email" style="color:#3b82f6;">$email</a></td></tr>
            <tr><td style="padding:8px 12px;font-size:13px;color:#94a3b8;">Sklep</td><td style="padding:8px 12px;font-size:14px;color:#3b82f6;"><a href="$storeUrl" style="color:#3b82f6;">$storeUrl</a></td></tr>
        </table>
        <table style="width:100%;border-collapse:collapse;margin-bottom:24px;">
            <tr style="background:#f8fafc;"><td style="padding:10px 12px;font-size:12px;text-transform:uppercase;letter-spacing:0.5px;color:#64748b;font-weight:600;">Zamówione usługi</td></tr>
            $itemsHtml
        </table>
        <div style="background:#f8fafc;border-radius:8px;padding:16px;margin-bottom:16px;">
            <table style="width:100%;border-collapse:collapse;">
                <tr><td style="padding:4px 0;font-size:13px;color:#64748b;">Netto</td><td style="padding:4px 0;font-size:13px;color:#0f172a;text-align:right;">{$amountNetto} PLN</td></tr>
                <tr><td style="padding:4px 0;font-size:13px;color:#64748b;">VAT (23%)</td><td style="padding:4px 0;font-size:13px;color:#0f172a;text-align:right;">{$amountVat} PLN</td></tr>
                <tr><td style="padding:8px 0 0;font-size:18px;font-weight:700;color:#0f172a;border-top:2px solid #e2e8f0;">Razem brutto</td><td style="padding:8px 0 0;font-size:18px;font-weight:700;color:#0f172a;text-align:right;border-top:2px solid #e2e8f0;">{$amountBrutto} PLN</td></tr>
            </table>
        </div>
        <div style="font-size:13px;color:#64748b;"><strong>Metoda płatności:</strong> $payLabel</div>
        $referralBlock
    </div>
    <div style="text-align:center;padding:16px;font-size:11px;color:#94a3b8;">$COMPANY &bull; $SITE_URL</div>
</div></body></html>
HTML;

// ═══ PROFORMA INVOICE HTML ═══
$dueDate = date('d.m.Y', strtotime('+2 days'));
$proformaItemsHtml = '';
$i = 1;
foreach ($items as $item) {
    // Extract price from item name (pattern: "— 1 000 zł" or "— 200 zł")
    $itemPrice = '—';
    $itemName = $item;
    if (preg_match('/—\s*([\d\s]+)\s*zł/u', $item, $m)) {
        $itemPrice = trim($m[1]) . ' zł';
        $itemName = trim(preg_replace('/\s*—\s*[\d\s]+\s*zł/u', '', $item));
    }
    $proformaItemsHtml .= "<tr><td style='padding:8px 12px;border:1px solid #e2e8f0;font-size:13px;'>$i</td><td style='padding:8px 12px;border:1px solid #e2e8f0;font-size:13px;'>$itemName</td><td style='padding:8px 12px;border:1px solid #e2e8f0;font-size:13px;text-align:right;'>$itemPrice</td></tr>";
    $i++;
}

$proformaTotalsHtml = $isSeoPogotowieOrder
    ? "<tr><td style=\"padding:4px 0;font-size:13px;color:#64748b;\">Wartość netto</td><td style=\"padding:4px 0;font-size:14px;color:#0f172a;text-align:right;font-weight:500;\">{$proformaNettoAmount} PLN</td></tr>"
        . "<tr><td style=\"padding:8px 0 0;font-size:18px;font-weight:700;color:#0f172a;border-top:2px solid #e2e8f0;\">Do zapłaty</td><td style=\"padding:8px 0 0;font-size:18px;font-weight:700;color:#0f172a;text-align:right;border-top:2px solid #e2e8f0;\">{$amountBrutto} PLN</td></tr>"
    : "<tr><td style=\"padding:4px 0;font-size:13px;color:#64748b;\">Wartość netto</td><td style=\"padding:4px 0;font-size:14px;color:#0f172a;text-align:right;font-weight:500;\">{$amountNetto} PLN</td></tr>"
        . "<tr><td style=\"padding:4px 0;font-size:13px;color:#64748b;\">Podatek VAT (23%)</td><td style=\"padding:4px 0;font-size:14px;color:#0f172a;text-align:right;font-weight:500;\">{$amountVat} PLN</td></tr>"
        . "<tr><td style=\"padding:8px 0 0;font-size:18px;font-weight:700;color:#0f172a;border-top:2px solid #e2e8f0;\">Do zapłaty</td><td style=\"padding:8px 0 0;font-size:18px;font-weight:700;color:#0f172a;text-align:right;border-top:2px solid #e2e8f0;\">{$amountBrutto} PLN</td></tr>";

$proformaHtml = <<<HTML
<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"></head>
<body style="font-family:Inter,-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,Arial,sans-serif;background:#f1f5f9;margin:0;padding:0;">
<div style="max-width:600px;margin:0 auto;">
    <div style="background:linear-gradient(135deg,#0f172a 0%,#1e3a5f 100%);padding:24px 32px;text-align:center;">
        $logoHtml
    </div>
    <div style="background:#fff;padding:32px;margin:0;">
        <h2 style="color:#0f172a;font-size:18px;margin:0 0 24px;text-align:center;">FAKTURA PRO FORMA nr PRO/$orderId/$orderDateShort</h2>

        <table style="width:100%;border-collapse:collapse;margin-bottom:24px;">
            <tr>
                <td style="width:50%;vertical-align:top;padding:12px;background:#f8fafc;border-radius:8px 0 0 8px;">
                    <div style="font-size:11px;text-transform:uppercase;letter-spacing:0.5px;color:#94a3b8;margin-bottom:8px;font-weight:600;">Sprzedawca</div>
                    <div style="font-size:13px;color:#0f172a;line-height:1.6;">
                        <strong>$COMPANY</strong><br>
                        $COMPANY_ADDR<br>
                        NIP: $COMPANY_NIP<br>
                        KRS: $COMPANY_KRS
                    </div>
                </td>
                <td style="width:50%;vertical-align:top;padding:12px;background:#f8fafc;border-radius:0 8px 8px 0;">
                    <div style="font-size:11px;text-transform:uppercase;letter-spacing:0.5px;color:#94a3b8;margin-bottom:8px;font-weight:600;">Nabywca</div>
                    <div style="font-size:13px;color:#0f172a;line-height:1.6;">
                        <strong>$company</strong><br>
                        $companyAddressLine
                        $name<br>
                        NIP: $nip<br>
                        E-mail: $email<br>
                        Telefon: $phone<br>
                        Sklep: $storeUrl
                    </div>
                </td>
            </tr>
        </table>

        <table style="width:100%;border-collapse:collapse;margin-bottom:24px;">
            <tr style="background:#0f172a;">
                <th style="padding:10px 12px;font-size:11px;text-transform:uppercase;letter-spacing:0.5px;color:#fff;text-align:left;border:1px solid #1e293b;">Lp.</th>
                <th style="padding:10px 12px;font-size:11px;text-transform:uppercase;letter-spacing:0.5px;color:#fff;text-align:left;border:1px solid #1e293b;">Nazwa usługi</th>
                <th style="padding:10px 12px;font-size:11px;text-transform:uppercase;letter-spacing:0.5px;color:#fff;text-align:right;border:1px solid #1e293b;">Wartość</th>
            </tr>
            $proformaItemsHtml
        </table>

        <div style="background:#f8fafc;border-radius:8px;padding:16px;margin-bottom:24px;">
            <table style="width:100%;border-collapse:collapse;">
                $proformaTotalsHtml
            </table>
        </div>

        <div style="background:#eff6ff;border-radius:8px;padding:16px;margin-bottom:24px;border-left:4px solid #3b82f6;">
            <div style="font-size:12px;text-transform:uppercase;letter-spacing:0.5px;color:#3b82f6;font-weight:600;margin-bottom:8px;">Dane do przelewu</div>
            <div style="font-size:13px;color:#0f172a;line-height:1.8;">
                <strong>Odbiorca:</strong> $COMPANY<br>
                <strong>Bank:</strong> $BANK_NAME<br>
                <strong>Nr konta:</strong> $BANK_ACCOUNT<br>
                <strong>Tytuł przelewu:</strong> Pro forma PRO/$orderId<br>
                <strong>Kwota:</strong> {$amountBrutto} PLN<br>
                <strong>Termin płatności:</strong> $dueDate
            </div>
        </div>

        <div style="font-size:11px;color:#94a3b8;line-height:1.6;margin-top:16px;">
            Dokument wystawiony dnia $orderDateShort. Proforma nie jest dokumentem księgowym.<br>
            Faktura VAT zostanie wystawiona po zaksięgowaniu wpłaty.<br>
            Kontakt telefoniczny: $SUPPORT_PHONE
        </div>
    </div>
    <div style="text-align:center;padding:16px;font-size:11px;color:#94a3b8;">$COMPANY &bull; $COMPANY_ADDR &bull; NIP: $COMPANY_NIP &bull; tel. $SUPPORT_PHONE</div>
</div></body></html>
HTML;

// ═══ BUYER EMAIL ═══
// ═══ ONBOARDING BLOCK (inline in buyer email for AI Booster) ═══
$description = $input['description'] ?? '';
$isAIBooster = (stripos($description, 'AI Visibility') !== false);
$isStarter = (stripos($description, 'STARTER') !== false);
$onboardingInline = '';

if ($isAIBooster) {
    $onboardingInline = '<div style="margin-top:24px;padding-top:20px;border-top:2px solid #e2e8f0;">'
        . '<p style="font-size:15px;font-weight:700;color:#0f172a;margin:0 0 12px;">Nastepne kroki</p>';

    if ($isStarter) {
        $onboardingInline .= '<p style="font-size:13px;color:#334155;line-height:1.7;margin:0 0 12px;">'
            . 'Aby uruchomic system, potrzebujemy od Ciebie:<br>'
            . '<strong>1.</strong> Login i haslo do WebAPI sklepu (Ustawienia &rarr; Integracje &rarr; WebAPI &rarr; Dodaj konto)<br>'
            . '<strong>2.</strong> Klucz API Google Gemini</p>'
            . '<p style="font-size:13px;color:#64748b;margin:0 0 8px;">Nie wiesz jak uzyskac klucz Gemini? Skonfigurujemy wszystko za Ciebie za <strong>200 zl netto</strong>.</p>'
            . '<p style="margin:0;"><a href="' . $SITE_URL . '/ai-visibility-booster?buy=config&amp;email=' . urlencode($email) . '&amp;order=' . $orderId . '" style="color:#3b82f6;font-weight:600;font-size:13px;">Zamow konfiguracje &rarr;</a></p>';
    } else {
        $onboardingInline .= '<p style="font-size:13px;color:#334155;line-height:1.7;margin:0 0 12px;">'
            . 'Potrzebujemy tylko jednej rzeczy:<br>'
            . '<strong>Login i haslo do WebAPI</strong> (Ustawienia &rarr; Integracje &rarr; WebAPI &rarr; Dodaj konto)</p>'
            . '<p style="font-size:13px;color:#16a34a;margin:0;">Klucz API, konfiguracja i wdrozenie — po naszej stronie.</p>';
    }

    $onboardingInline .= '<p style="font-size:12px;color:#94a3b8;margin:12px 0 0;">Odpowiedz na tego maila z danymi dostepowymi.</p></div>';
}


$buyerSubject = "Potwierdzenie zamówienia #$orderId — Booster Engine";
$buyerHeader = str_replace('__SUBTITLE__', 'Potwierdzenie zamówienia', $headerBlock);
$buyerHtml = <<<HTML
<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"></head>
<body style="font-family:Inter,-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,Arial,sans-serif;background:#f1f5f9;margin:0;padding:0;">
<div style="max-width:600px;margin:0 auto;">
    $buyerHeader
    <div style="background:#fff;border-radius:12px;padding:32px;margin:24px;box-shadow:0 1px 3px rgba(0,0,0,0.08);">
        <div style="text-align:center;margin-bottom:24px;">
            <div style="display:inline-block;width:56px;height:56px;background:#dcfce7;border-radius:50%;line-height:56px;font-size:28px;">✓</div>
            <h2 style="font-size:20px;color:#0f172a;margin:16px 0 4px;">Dziękujemy za zamówienie!</h2>
            <p style="font-size:14px;color:#64748b;margin:0;">Zamówienie <strong>#$orderId</strong> zostało przyjęte.</p>
        </div>
        <div style="background:#eff6ff;border-radius:8px;padding:16px;margin-bottom:24px;text-align:center;">
            <div style="font-size:13px;color:#3b82f6;font-weight:600;">Co dalej?</div>
            <p style="font-size:13px;color:#334155;margin:8px 0 0;line-height:1.5;">Skontaktujemy się w ciągu 24h.<br><a href="mailto:$SELLER_EMAIL" style="color:#3b82f6;">$SELLER_EMAIL</a></p>
        </div>
        <table style="width:100%;border-collapse:collapse;margin-bottom:24px;">
            <tr style="background:#f8fafc;"><td style="padding:10px 12px;font-size:12px;text-transform:uppercase;letter-spacing:0.5px;color:#64748b;font-weight:600;">Zamówione usługi</td></tr>
            $itemsHtml
        </table>
        <div style="background:#f8fafc;border-radius:8px;padding:16px;margin-bottom:16px;">
            <table style="width:100%;border-collapse:collapse;">
                <tr><td style="padding:4px 0;font-size:13px;color:#64748b;">Netto</td><td style="padding:4px 0;font-size:13px;color:#0f172a;text-align:right;">{$amountNetto} PLN</td></tr>
                <tr><td style="padding:4px 0;font-size:13px;color:#64748b;">VAT (23%)</td><td style="padding:4px 0;font-size:13px;color:#0f172a;text-align:right;">{$amountVat} PLN</td></tr>
                <tr><td style="padding:8px 0 0;font-size:18px;font-weight:700;color:#0f172a;border-top:2px solid #e2e8f0;">Razem brutto</td><td style="padding:8px 0 0;font-size:18px;font-weight:700;color:#0f172a;text-align:right;border-top:2px solid #e2e8f0;">{$amountBrutto} PLN</td></tr>
            </table>
        </div>
        <div style="font-size:13px;color:#64748b;"><strong>Metoda płatności:</strong> $payLabel</div>
        $onboardingInline
    </div>
    <div style="text-align:center;padding:24px;font-size:12px;color:#94a3b8;line-height:1.6;">
        $COMPANY<br>$SITE_URL<br>
        tel. $SUPPORT_PHONE<br>
        <a href="$SITE_URL/regulamin.html" style="color:#64748b;">Regulamin</a> &bull;
        <a href="$SITE_URL/polityka-prywatnosci.html" style="color:#64748b;">Polityka Prywatności</a>
    </div>
</div></body></html>
HTML;

// ═══ Send emails ═══
$headers  = "MIME-Version: 1.0\r\n";
$headers .= "Content-Type: text/html; charset=UTF-8\r\n";
$headers .= "From: Booster Engine <$SELLER_EMAIL>\r\n";
$headers .= "Reply-To: $SELLER_EMAIL\r\n";

$sentSeller = mail($SELLER_EMAIL, $sellerSubject, $sellerHtml, $headers);

// For traditional transfer: send proforma + confirmation
if ($payMethod === 'przelew_tradycyjny') {
    $sentBuyer = mail($email, "Faktura pro forma #$orderId — Booster Engine", $proformaHtml, $headers);
} else {
    $sentBuyer = mail($email, $buyerSubject, $buyerHtml, $headers);
}
// (Onboarding is now inline in buyer email — no separate send needed)


// Save order to file
$orderData = [
    'orderId' => $orderId,
    'date' => $orderDate,
    'name' => $name,
    'company' => $company,
    'companyAddress' => $companyAddress,
    'nip' => $nip,
    'phone' => $phone,
    'email' => $email,
    'storeUrl' => $storeUrl,
    'payMethod' => $payMethod,
    'amountNetto' => $amountNetto,
    'amountVat' => $amountVat,
    'amountBrutto' => $amountBrutto,
    'items' => $items,
    'referralSource' => $referralSource,
    'referralCampaign' => $referralCampaign,
    'referralEmail' => $referralEmail,
    'sentSeller' => $sentSeller,
    'sentBuyer' => $sentBuyer
];
file_put_contents($ordersDir . "/order_{$orderId}.json", json_encode($orderData, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE));

// Log
$logLine = "$orderDate | #$orderId | $email | $name | {$amountBrutto} PLN | $payMethod | seller=$sentSeller buyer=$sentBuyer\n";
file_put_contents(__DIR__ . '/orders.log', $logLine, FILE_APPEND | LOCK_EX);

echo json_encode([
    'success'  => true,
    'orderId'  => $orderId,
    'sentSeller' => $sentSeller,
    'sentBuyer'  => $sentBuyer
]);
