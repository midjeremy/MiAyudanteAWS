<?php
function api_get(string $ruta): ?array{
    $ch = curl_init("http://44.196.193.153" . $ruta);
    curl_setopt_array($ch,[
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_TIMEOUT => 5,
    ]);
    $respuesta = curl_exec($ch);
    $codigo = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    
    return ($codigo === 200) ? json_decode($respuesta, true) : null;
}