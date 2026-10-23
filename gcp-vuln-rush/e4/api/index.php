<?php
// A2B の確認用の小さな API。/orders?user=ID で、その利用者の注文を返す(認可の確認は、わざと入れていない版と入れた版を切り替える)
header('Content-Type: application/json');
$orders = ['alice' => [['id' => 1, 'item' => 'book']], 'bob' => [['id' => 2, 'item' => 'pen']]];
$user = $_GET['user'] ?? '';
$caller = '';
if (!empty($_SERVER['HTTP_X_APIGATEWAY_API_USERINFO'])) {          // API Gateway が検証した JWT の中身(base64url)
    $info = json_decode(base64_decode(strtr($_SERVER['HTTP_X_APIGATEWAY_API_USERINFO'], '-_', '+/')), true);
    $caller = $info['email'] ?? '';
}
$check = getenv('AUTHZ_CHECK') === '1';
$owner = ['alice' => getenv('ALICE_EMAIL'), 'bob' => getenv('BOB_EMAIL')][$user] ?? null;
if ($check && $caller !== $owner) { http_response_code(403); echo json_encode(['error' => 'forbidden']); exit; }
echo json_encode(['user' => $user, 'caller' => $caller, 'orders' => $orders[$user] ?? []]);
