<?php
// Convierte las ofertas que entrega la API de Django en los datos que usan las vistas.

const TAMANO_PAGINA = 20;

function formatear_clp($monto): string{
    return '$' . number_format((int) $monto, 0, ',', '.');
}

// Arancel comparable entre instituciones (anual cuando existe).
// NUEVO: si la API lo calculó desde la cuota mensual (Duoc), se marca como referencial.
function arancel_de_oferta(array $row): array{
    $referencia = $row['arancel_referencia'] ?? null;
    if (!$referencia) {
        return ['monto' => 0, 'texto' => 'Sin información', 'periodo' => 'arancel no publicado'];
    }
    $periodo = 'arancel ' . $referencia['periodo'];
    if (!empty($referencia['calculado'])) {
        $periodo .= ' referencial';
    }
    return [
        'monto' => (int) $referencia['monto'],
        'texto' => formatear_clp($referencia['monto']),
        'periodo' => $periodo,
    ];
}

// NUEVO: años a partir de meses, con una coma decimal (36 -> "3 años", 32 -> "2,7 años")
function anos_desde_meses(int $meses): string{
    $anos = round($meses / 12, 1);
    $texto = rtrim(rtrim(number_format($anos, 1, ',', ''), '0'), ',');
    return $texto . ($anos == 1 ? ' año' : ' años');
}

// NUEVO: duración para mostrar. Usa los meses de la API (bimestres o semestres) y, si no hay,
// los semestres como antes. En una carrera con varias modalidades muestra el rango ("2,7 a 4 años").
function duracion_de_oferta(array $row): string{
    $meses = $row['duracion_meses'] ?? null;
    if (is_array($meses)) {  // vista de carreras: {'min': 32, 'max': 48}
        $minimo = (int) ($meses['min'] ?? 0);
        $maximo = (int) ($meses['max'] ?? 0);
        if ($minimo && $maximo && $minimo !== $maximo) {
            return str_replace(' años', '', anos_desde_meses($minimo)) . ' a ' . anos_desde_meses($maximo);
        }
        $meses = $minimo ?: null;
    }
    if ($meses) {
        return anos_desde_meses((int) $meses);
    }
    $semestres = (int) ($row['duracion_semestres'] ?? 0);
    return $semestres ? anos_desde_meses($semestres * 6) : 'No informada';
}

function oferta_a_tarjeta(array $row): array{
    $institucion = $row['institucion'] ?? '';
    $inst_clave = strtolower($row['institucion_codigo'] ?? '');
    $nombre_carrera = $row['carrera'] ?? '';
    $area_clave = (stripos($nombre_carrera, 'diseño') !== false) ? 'diseno' : 'tecnologia';
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
        "duracion" => duracion_de_oferta($row),  // NUEVO: antes solo semestres
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
        'duracion_meses' => $row['duracion_meses'] ?? null,  // NUEVO
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