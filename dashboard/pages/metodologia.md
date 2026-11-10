---
title: Metodología
description: Fuente, definiciones, hora de corte y calidad de los datos.
sidebar_position: 8
---

```sql meta
select * from monitor.metadatos
```

## Fuente

Los datos vienen de [cargadorespublicos.cl](https://cargadorespublicos.cl), plataforma pública de interoperabilidad de la Superintendencia de Electricidad y Combustibles (SEC). La plataforma muestra solo el estado actual; este monitor guarda una foto cada día a las 00:00 (hora de Chile) para construir historia.

La población por comuna proviene del Censo de Población y Vivienda 2024 (INE).

<Grid cols=3>
<BigValue data={meta} value=primera_foto title="Primera foto" fmt="dd-mm-yyyy"/>
<BigValue data={meta} value=ultima_foto title="Última foto" fmt="dd-mm-yyyy"/>
<BigValue data={meta} value=n_fotos title="Fotos acumuladas" fmt="#,##0"/>
</Grid>

## Definiciones

| Término | Significado |
| --- | --- |
| Ubicación | Lugar declarado con uno o más puntos de carga (una electrolinera, un estacionamiento). |
| Punto de carga (EVSE) | Equipo que carga un vehículo a la vez. Es la unidad principal de este monitor. |
| Conector | Enchufe o cable de un punto. Un punto puede tener varios conectores de distinto estándar. |
| Lento / rápido | Potencia máxima del punto menor a 50 kW / de 50 kW o más. |
| AC / DC | Un punto es DC si tiene al menos un conector de corriente continua. |
| Operativo | Estado "Disponible" u "Ocupado" en la foto de las 00:00. |
| Fuera de línea | El punto no está reportando su estado a la plataforma. |
| No disponible | El operador informa que el punto no puede usarse. |
| Puntos por 100 mil habitantes | Puntos de carga de la zona / población censada 2024 × 100.000. |

## Calidad de los datos

- **Sin fecha de instalación.** La fuente no publica cuándo se instaló cada punto. El crecimiento histórico es una estimación; el crecimiento medido parte con la primera foto.
- **Operador sin informar.** Algunas ubicaciones no declaran operador y se agrupan como "Sin operador informado".
- **Estándar sin informar.** Algunos conectores traen "Favor actualizar valor" y se muestran como "No informado".
- **Registros de prueba.** Se excluyen ubicaciones cuyo operador o nombre indica que son de prueba.
- **Una foto al día.** La disponibilidad refleja el estado a las 00:00, no el uso a lo largo del día.

## Privacidad

No se guardan ni publican datos de contacto de operadores o propietarios (correos, teléfonos, sitios web, direcciones de empresas, RUT). El proceso usa una lista blanca de campos: solo se conserva lo que aparece en este dashboard.

## Código

El proceso de actualización y este dashboard son de código abierto en [GitHub](https://github.com/JosueIgnacio/monitor-ic-chile).
