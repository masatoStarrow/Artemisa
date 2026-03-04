"""
DEPRECATED — Este script ya no debe usarse.

El seed de usuarios ahora se ejecuta exclusivamente desde el API Gateway (Atenea)
mediante el comando de management:

    sudo docker-compose exec gateway python manage.py seed_users

Ese comando usa el flujo dual-write (CreateUserGateway) para crear cada usuario
en la Gateway DB (con password hash) Y en este servicio (mismo UUID, sin password),
garantizando consistencia de UUIDs entre ambas bases de datos.

Razón del cambio: si se ejecutaba este script directamente, los UUIDs generados
aquí diferían de los generados en Atenea, rompiendo el vínculo entre servicios.
"""

raise DeprecationWarning(
    "seed_users de Artemisa está deprecado. "
    "Usar: sudo docker-compose exec gateway python manage.py seed_users"
)
