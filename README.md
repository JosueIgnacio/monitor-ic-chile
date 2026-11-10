# Monitor IC Chile

Dashboard de la infraestructura de carga pública para vehículos eléctricos en Chile, actualizado cada día a las 00:00 (hora de Chile) con datos de [cargadorespublicos.cl](https://cargadorespublicos.cl).

- **Datos:** un ETL en Python guarda cada noche una foto limpia de la red (sin datos de contacto) en la rama `data`. Con esas fotos se construye la historia de disponibilidad, días fuera de servicio y crecimiento.
- **Dashboard:** [Evidence](https://evidence.dev) (open source), con 8 páginas: Resumen, Mapa, Territorio, Crecimiento, Operadores, Disponibilidad, Tarifas y Metodología.
- **Población:** Censo 2024 (INE), para indicadores por habitante.

Para mantenerlo o contribuir, lee [CLAUDE.md](CLAUDE.md).
