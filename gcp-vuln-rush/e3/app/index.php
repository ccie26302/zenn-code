<?php
// 外への通信の確認用: 決まった2つの宛先(外のサイトと Google の API)に届くかだけを返す。宛先は利用者から変えられない
header('Content-Type: application/json');
function reach($url) {
    $ch = curl_init($url); curl_setopt_array($ch, [CURLOPT_RETURNTRANSFER => true, CURLOPT_NOBODY => true, CURLOPT_TIMEOUT => 8, CURLOPT_CONNECTTIMEOUT => 8]);
    curl_exec($ch); $code = curl_getinfo($ch, CURLINFO_HTTP_CODE); $err = curl_error($ch); curl_close($ch);
    return ['http' => $code, 'error' => $err];
}
echo json_encode(['external_site' => reach('https://example.com/'), 'google_api' => reach('https://storage.googleapis.com/')]);
