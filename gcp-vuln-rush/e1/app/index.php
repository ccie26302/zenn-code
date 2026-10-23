<?php
header('Content-Type: application/json');
echo json_encode(['php_version' => PHP_VERSION, 'sapi' => php_sapi_name(), 'os' => php_uname('s') . ' ' . php_uname('r')]);
