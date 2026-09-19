<?php
/**
 * PostHog Capture Helper
 * Sends server-side events to PostHog
 */

function posthog_capture($event, $distinct_id, $properties = []) {
    $apiKey = getenv('POSTHOG_API_KEY') ?: '';
    $url = 'https://eu.i.posthog.com/capture/';

    $payload = [
        'api_key' => $apiKey,
        'event' => $event,
        'distinct_id' => $distinct_id,
        'properties' => $properties
    ];

    $ch = curl_init($url);
    curl_setopt_array($ch, [
        CURLOPT_POST => true,
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_HTTPHEADER => ['Content-Type: application/json'],
        CURLOPT_POSTFIELDS => json_encode($payload),
        CURLOPT_TIMEOUT => 5
    ]);

    $response = curl_exec($ch);
    curl_close($ch);

    return $response;
}
