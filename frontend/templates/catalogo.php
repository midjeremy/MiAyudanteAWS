<?php
// Convierte las ofertas que entrega la API de Django en los datos que usan las vistas.

const TAMANO_PAGINA = 20;

function formatear_clp($monto): string{
    return '$' . number_format((int) $monto, 0, ',', '.');
}

// Muestra el arancel con el período que publica la institución, sin convertirlo
function arancel_de_oferta(array $row): array{
    $referencia = $row['arancel_referencia'] ?? null;
    if (!$referencia) {
        return ['monto' => 0, 'texto' => 'Sin información', 'periodo' => 'arancel no publicado'];
    }
    return [
        'monto' => (int) $referencia['monto'],
        'texto' => formatear_clp($referencia['monto']),
        'periodo' => 'arancel ' . $referencia['periodo'],
    ];
}

function oferta_a_tarjeta(array $row): array{
    $institucion = $row['institucion'] ?? '';
    $inst_clave = strtolower($row['institucion_codigo'] ?? '');
    $nombre_carrera = $row['carrera'] ?? '';
    $area_clave = (stripos($nombre_carrera, 'diseño') !== false) ? 'diseno' : 'tecnologia';
    $semestres = (int) ($row['duracion_semestres'] ?? 0);
    $arancel = arancel_de_oferta($row);

    return [
        "id" => $row['id'],
        "nombre" => $nombre_carrera,
        "institucion" => $institucion,
        "inst_clave" => $inst_clave,
        "logo_texto" => ($inst_clave === 'duoc') ? 'DuocUC' : 'inacap',
        "logo_clase" => ($inst_clave === 'duoc') ? 'duoc-logo' : 'square-logo',
        "categoria" => ($area_clave === 'diseno') ? 'Diseño' : 'Tecnología',
        "area_clave" => $area_clave,
        "categoria_clase" => ($area_clave === 'diseno') ? 'badge-pink' : 'badge-blue',
        "ubicacion" => $row['sede'] ?? '',
        "modalidad" => $row['modalidad'] ?? 'No informada',
        "duracion" => $semestres ? round($semestres / 2, 1) . ' años' : 'No informada',
        "arancel" => $arancel['texto'],
        "arancel_periodo" => $arancel['periodo'],
    ];
}

// Tarjeta de una carrera agrupada (vista "carreras"): resume todas sus sedes y jornadas
function carrera_a_tarjeta(array $row): array{
    $tarjeta = oferta_a_tarjeta([
        'id' => $row['id'],
        'institucion' => $row['institucion'] ?? '',
        'institucion_codigo' => $row['institucion_codigo'] ?? '',
        'carrera' => $row['carrera'] ?? '',
        'duracion_semestres' => $row['duracion_semestres'] ?? null,
        'modalidad' => implode(' / ', $row['modalidades'] ?? []) ?: 'No informada',
        'arancel_referencia' => $row['arancel_desde'] ?? null,
    ]);
    $total_sedes = (int) ($row['total_sedes'] ?? 0);
    $tarjeta['ubicacion'] = ($total_sedes === 1) ? ($row['sedes'][0] ?? '1 sede') : $total_sedes . ' sedes';
    if (!empty($row['arancel_desde'])) {
        $tarjeta['arancel_periodo'] = 'desde · ' . $tarjeta['arancel_periodo'];
    }
    $tarjeta['es_carrera'] = true;
    return $tarjeta;
}